import openai  
import os
import json
import yaml
import argparse
import base64
from datetime import datetime

# --------- Load API Key from config.json ---------
def load_api_key():
    with open("config.json", "r") as f:
        config = json.load(f)
        return config["open_ai_key"]

openai.api_key = load_api_key()

# --------- Helper: Load scene session ---------
def load_scene_session(path):
    with open(path, 'r') as f:
        return json.load(f)

# --------- Helper: Load existing DynamicCoding.json files ---------
def load_existing_generated_objects(folder):
    summaries = []
    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            with open(os.path.join(folder, filename), 'r') as f:
                data = json.load(f)
                obj = data.get("object", "<unknown>")
                effect_names = [p.get("effectName") for p in data.get("particle_json", [])]
                summary = f"• \"{obj}\": uses effects {effect_names}"
                summaries.append(summary)
    return summaries

# --------- Helper: Load base prompt YAML ---------
def load_base_prompt_template_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)
    return yaml_data["prompt_template"]

# --------- Helper: Build Prompt ---------
def build_prompt(scene_json, existing_objects_summaries, base_template, object_prompt):
    premise = scene_json.get("premise", "")
    detail = scene_json.get("prompt", "")
    furniture = ', '.join(f'"{f.get("name", "Unnamed")}"' for f in scene_json.get("SceneObjects", []))
    spots = ', '.join(f'"{s.get("id", "")}"' for s in scene_json.get("generateSpots", []))
    existing_summary = '\n'.join(existing_objects_summaries)

    prompt_input = detail.strip()

    return base_template.format(
        premise=premise,
        prompt=prompt_input,
        furniture=furniture,
        generate_spots=spots,
        existing_objects=existing_summary
    ) + f"\n\nObject Prompt:\n{object_prompt.strip()}"

# --------- Call OpenAI ---------
def call_openai(prompt):
    client = openai.OpenAI(api_key=load_api_key())
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a Lua generation agent for Unity simulation."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5
    )
    return response.choices[0].message.content

# --------- Vision: Extract formula from image ---------
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def extract_formula_from_image(image_path, user_prompt="What is the formula in this image? Return it as LaTeX."):
    base64_image = encode_image(image_path)
    response = openai.ChatCompletion.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ],
        max_tokens=1000
    )
    return response["choices"][0]["message"]["content"]

# --------- Vision-only Dynamic Generation ---------
def vision_only_generate(image_path, urlid):
    formula = extract_formula_from_image(image_path)
    object_prompt = (
        f"Task: Given the following formula extracted from an image, create a Unity-compatible Lua + JSON configuration "
        f"that visually simulates the concept using particle effects or object behavior.\n\n"
        f"Formula:\n{formula.strip()}\n\n"
        "Expected Output: A JSON with \"object\", \"comment\", \"created_at\", and either \"param_ui_lua\" or \"param_ui_particle\". "
        "Use visual metaphors if needed."
    )
    result = call_openai(object_prompt)
    dynamic_folder = os.path.join("objects", urlid)
    os.makedirs(dynamic_folder, exist_ok=True)
    output_path = os.path.join(dynamic_folder, f"{urlid}_DynamicCoding.json")
    with open(output_path, 'w') as f:
        f.write(result)
    print(f"[✓] Saved to {output_path}")
    return result

# --------- CLI Entry Point ---------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lua Generator CLI")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    gen_parser = subparsers.add_parser("generate")
    gen_parser.add_argument("scene_json")
    gen_parser.add_argument("prompt_yaml")
    gen_parser.add_argument("urlid")
    gen_parser.add_argument("object_prompt")
    gen_parser.add_argument("--update-others", action="store_true")

    mod_parser = subparsers.add_parser("modify")
    mod_parser.add_argument("existing_json")
    mod_parser.add_argument("prompt_yaml")
    mod_parser.add_argument("object_prompt")
    mod_parser.add_argument("--update-others", action="store_true")

    vision_parser = subparsers.add_parser("vision")
    vision_parser.add_argument("image_path")
    vision_parser.add_argument("--prompt", default="What is the formula in this image? Return it as LaTeX.")
    vision_parser.add_argument("--scene_json")
    vision_parser.add_argument("--prompt_yaml")
    vision_parser.add_argument("--urlid")
    vision_parser.add_argument("--update-others", action="store_true")

    vision_only_parser = subparsers.add_parser("vision-generate")
    vision_only_parser.add_argument("image_path")
    vision_only_parser.add_argument("urlid")

    args = parser.parse_args()

    if args.mode == "generate":
        scene = load_scene_session(args.scene_json)
        folder = os.path.join("objects", args.urlid)
        os.makedirs(folder, exist_ok=True)
        existing = load_existing_generated_objects(folder)
        base = load_base_prompt_template_yaml(args.prompt_yaml)
        full_prompt = build_prompt(scene, existing, base, args.object_prompt)
        result = call_openai(full_prompt)
        with open(os.path.join(folder, f"{args.urlid}_DynamicCoding.json"), 'w') as f:
            f.write(result)

    elif args.mode == "modify":
        with open(args.existing_json, 'r') as f:
            original_data = json.load(f)
        base_prompt = load_base_prompt_template_yaml(args.prompt_yaml)
        prompt = (
            f"The current object is: {original_data.get('object_name', 'Unknown')} (don't change it)\n\n"
            f"Original Lua Code:\n{original_data.get('lua_code', '')}\n\n"
            f"Original Particle Effects:\n{json.dumps(original_data.get('particle_json', []), indent=2)}\n\n"
            f"Edit Instruction:\n{args.object_prompt.strip()}"
        )
        full_prompt = base_prompt + "\n\n" + prompt
        result = call_openai(full_prompt)
        with open(args.existing_json, 'w') as f:
            f.write(result)

    elif args.mode == "vision":
        if args.scene_json and args.prompt_yaml and args.urlid:
            formula = extract_formula_from_image(args.image_path, args.prompt)
            object_prompt = f"The extracted formula is:\n{formula.strip()}\n\nVisualize this in Unity using Lua/particles."
            scene = load_scene_session(args.scene_json)
            folder = os.path.join("objects", args.urlid)
            os.makedirs(folder, exist_ok=True)
            existing = load_existing_generated_objects(folder)
            base = load_base_prompt_template_yaml(args.prompt_yaml)
            full_prompt = build_prompt(scene, existing, base, object_prompt)
            result = call_openai(full_prompt)
            with open(os.path.join(folder, f"{args.urlid}_DynamicCoding.json"), 'w') as f:
                f.write(result)
        else:
            print(extract_formula_from_image(args.image_path, args.prompt))

    elif args.mode == "vision-generate":
        vision_only_generate(args.image_path, args.urlid)

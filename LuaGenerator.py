import openai  
import os
import json
import yaml
import argparse
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

# --------- Main Functions ---------
def generate_dynamic_lua(scene_json_path, base_prompt_yaml_path, urlid, object_prompt, update_others=False):
    scene = load_scene_session(scene_json_path)
    dynamic_folder = os.path.join("objects", urlid)
    os.makedirs(dynamic_folder, exist_ok=True)

    existing_objects = load_existing_generated_objects(dynamic_folder)
    base_prompt = load_base_prompt_template_yaml(base_prompt_yaml_path)
    full_prompt = build_prompt(scene, existing_objects, base_prompt, object_prompt)
    result = call_openai(full_prompt)

    # Save result
    output_path = os.path.join(dynamic_folder, f"{urlid}_DynamicCoding.json")
    with open(output_path, 'w') as f:
        f.write(result)
    print(f"Lua JSON generated and saved to: {output_path}")

    if update_others:
        update_other_virtual_objects(scene, urlid, base_prompt_yaml_path, object_prompt)

    return result

def update_other_virtual_objects(scene, new_urlid, base_prompt_yaml_path, new_object_prompt):
    for spot in scene.get("generateSpots", []):
        other_id = spot.get("id")
        if other_id != new_urlid:
            obj_path = os.path.join("objects", other_id, f"{other_id}_DynamicCoding.json")
            if os.path.exists(obj_path):
                print(f"↪ Updating object: {other_id} in response to new object {new_urlid}...")
                try:
                    with open(obj_path, 'r') as f:
                        existing_json = json.load(f)

                    original_lua = existing_json.get("lua_code", "")
                    object_name = existing_json.get("object", other_id)
                    old_comment = existing_json.get("comment", "")

                    object_summary = f"Existing object: {object_name}\nLua Code:\n{original_lua}\nComment:\n{old_comment}"
                    update_prompt = f"{object_summary}\n\nNew object added: {new_object_prompt}\nPlease revise the Lua code of {object_name} if needed."

                    base_prompt = load_base_prompt_template_yaml(base_prompt_yaml_path)
                    full_prompt = build_prompt(scene, [], base_prompt, update_prompt)
                    result = call_openai(full_prompt)

                    updated_data = json.loads(result)
                    updated_data["created_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

                    with open(obj_path, "w") as f:
                        json.dump(updated_data, f, indent=2)
                    print(f"✅ Updated: {other_id}")
                except Exception as e:
                    print(f"⚠️ Failed to update {other_id}: {e}")

def modify_dynamic_lua(existing_json_path, base_prompt_yaml_path, object_prompt, update_others=False):
    with open(existing_json_path, 'r') as f:
        original_data = json.load(f)

    base_prompt = load_base_prompt_template_yaml(base_prompt_yaml_path)

    original_lua = original_data.get("lua_code", "")
    object_name = original_data.get("object", "Unknown")

    prompt = f"The current object is: {object_name}\n\nOriginal Lua Code:\n{original_lua}\n\nEdit Instruction:\n{object_prompt.strip()}"

    full_prompt = base_prompt + f"\n\n{prompt}"
    result = call_openai(full_prompt)

    with open(existing_json_path, 'w') as f:
        f.write(result)
    print(f"Modified Lua JSON overwritten to: {existing_json_path}")

    if update_others:
        urlid = os.path.basename(existing_json_path).split("_")[0]
        scene_path = f"{urlid}_scene.json"
        if os.path.exists(scene_path):
            scene = load_scene_session(scene_path)
            update_other_virtual_objects(scene, urlid, base_prompt_yaml_path, object_prompt)
        else:
            print(f"⚠️ Cannot update others: Scene file not found for {urlid}")

    return result

# --------- CLI Entry Point ---------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate or modify Lua behavior using OpenAI.")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    gen_parser = subparsers.add_parser("generate")
    gen_parser.add_argument("scene_json", help="Path to scene_session.json")
    gen_parser.add_argument("prompt_yaml", help="Path to base_prompt.yaml")
    gen_parser.add_argument("urlid", help="URL ID used to determine output path")
    gen_parser.add_argument("object_prompt", help="Prompt describing the object to generate")
    gen_parser.add_argument("--update-others", action="store_true", help="Update other virtual objects if needed")

    mod_parser = subparsers.add_parser("modify")
    mod_parser.add_argument("existing_json", help="Path to existing DynamicCoding.json to be modified")
    mod_parser.add_argument("prompt_yaml", help="Path to base_prompt.yaml")
    mod_parser.add_argument("object_prompt", help="Prompt describing the modification")
    mod_parser.add_argument("--update-others", action="store_true", help="Update other virtual objects if needed")

    args = parser.parse_args()

    if args.mode == "generate":
        generate_dynamic_lua(args.scene_json, args.prompt_yaml, args.urlid, args.object_prompt, args.update_others)
    elif args.mode == "modify":
        modify_dynamic_lua(args.existing_json, args.prompt_yaml, args.object_prompt, args.update_others)

import openai
import os
import json
import yaml
import argparse
from datetime import datetime

# Make sure to set your API key as an environment variable or replace this line with your actual key.
openai.api_key = os.getenv("OPENAI_API_KEY")
urlid=""

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
                summary = f"\u2022 \"{obj}\": uses effects {effect_names}"
                summaries.append(summary)
    return summaries

# --------- Helper: Load base prompt YAML ---------
def load_base_prompt_template_yaml(path):
    with open(path, 'r') as f:
        yaml_data = yaml.safe_load(f)
    return yaml_data["prompt_template"]

# --------- Helper: Build Prompt ---------
def build_prompt(scene_json, existing_objects_summaries, base_template):
    premise = scene_json.get("premise", "")
    detail = scene_json.get("prompt", "")
    furniture = ', '.join(f'"{f.get("name", "Unnamed")}"' for f in scene_json.get("furniture", []))
    spots = ', '.join(f'"{s.get("id", "")}"' for s in scene_json.get("generateSpots", []))
    existing_summary = '\n'.join(existing_objects_summaries)

    return base_template.format(
        premise=premise,
        prompt=detail,
        furniture=furniture,
        generate_spots=spots,
        existing_objects=existing_summary
    )

# --------- Call OpenAI ---------
def call_openai(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a Lua generation agent for Unity simulation."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5
    )
    return response['choices'][0]['message']['content']

# --------- Main Function ---------
def generate_dynamic_lua(scene_json_path, dynamic_folder, base_prompt_yaml_path, urlid):
    scene = load_scene_session(scene_json_path)
    existing_objects = load_existing_generated_objects(dynamic_folder)
    base_prompt = load_base_prompt_template_yaml(base_prompt_yaml_path)
    full_prompt = build_prompt(scene, existing_objects, base_prompt)
    result = call_openai(full_prompt)

    # Save result
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    output_path = os.path.join(dynamic_folder, f"{urlid}_DynamicCoding.json")
    with open(output_path, 'w') as f:
        f.write(result)
    print(f"✅ Lua JSON generated and saved to: {output_path}")
    return result

# --------- CLI Entry Point ---------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Lua behavior from scene session using OpenAI.")
    parser.add_argument("scene_json", help="Path to scene_session.json")
    parser.add_argument("dynamic_folder", help="Folder where DynamicCoding_*.json files are stored")
    parser.add_argument("prompt_yaml", help="Path to base_prompt.yaml")
    parser.add_argument("urlid", help="URL ID for the session (optional, can be used for logging or tracking)")

    args = parser.parse_args()

    generate_dynamic_lua(args.scene_json, args.dynamic_folder, args.prompt_yaml, args.urlid)

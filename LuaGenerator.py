import openai
import os
import json
import yaml
import argparse
import base64
import re
from datetime import datetime

# --------- Load API Key from config.json ---------
def load_api_key():
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        return config["open_ai_key"]

openai.api_key = load_api_key()

# --------- Safe Template Filler (no brace parsing) ---------
def fill_template_loose(template, fields):
    """
    Replace only placeholders we provide, without interpreting other braces.
    Leaves unknown {like_this} intact so JSON blocks with braces are safe.
    """
    out = template
    for k in sorted(fields.keys(), key=len, reverse=True):
        out = out.replace("{" + k + "}", str(fields[k]))
    return out

# --------- Helper Functions ---------
def load_scene_session(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_existing_generated_objects(folder):
    summaries = []
    if not os.path.isdir(folder):
        return summaries
    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            p = os.path.join(folder, filename)
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                continue
            obj = data.get("object_name") or data.get("object") or "<unknown>"
            effect_names = [p.get("effectName") for p in data.get("particle_json", [])]
            summaries.append(f"• \"{obj}\": uses effects {effect_names}")
    return summaries

def load_base_prompt_template_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)
    return yaml_data["prompt_template"]

def build_prompt(scene_json, existing_objects_summaries, base_template, object_prompt):
    premise = scene_json.get("premise", "")
    detail = scene_json.get("prompt", "")

    scene_objects_list = scene_json.get("SceneObjects", []) or []
    generate_spots_list = scene_json.get("generateSpots", []) or []

    # Template uses: "SceneObjects": [{scene_objects}] and [{generate_spots}]
    # Provide comma-separated JSON entries (no outer brackets).
    scene_objects_entries = ", ".join(json.dumps(item, ensure_ascii=False) for item in scene_objects_list)
    generate_spots_entries = ", ".join(json.dumps(item, ensure_ascii=False) for item in generate_spots_list)

    fields = {
        "premise": premise,
        "prompt": (detail or "").strip(),
        "existing_objects": "\n".join(existing_objects_summaries),
        "scene_objects": scene_objects_entries,
        "generate_spots": generate_spots_entries,
        # Back-compat aliases (harmless if unused)
        "scene_objects_json": json.dumps(scene_objects_list, ensure_ascii=False),
        "generate_spots_json": json.dumps(generate_spots_list, ensure_ascii=False),
        "furniture": "",
    }

    filled = fill_template_loose(base_template, fields)
    return f"{filled}\n\nObject Prompt:\n{object_prompt.strip()}"

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

# --------- Update Others ---------
def update_other_virtual_objects(scene_json, new_urlid, prompt_template, object_prompt):
    print(f"[Update] Trying to update other objects in response to: {new_urlid}")

    objects_dir = "objects"
    if not os.path.exists(objects_dir):
        print("[Error] No 'objects' directory found.")
        return

    # Only update virtual objects in current scene's generateSpots
    all_ids = [spot.get("id") for spot in scene_json.get("generateSpots", [])]

    for obj_id in all_ids:
        if obj_id == new_urlid:
            continue  # skip the one we just created

        existing_path = os.path.join(objects_dir, obj_id, f"{obj_id}_DynamicCoding.json")
        if not os.path.exists(existing_path):
            print(f"[Skip] Missing: {existing_path}")
            continue

        try:
            with open(existing_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
        except Exception as e:
            print(f"[Error] Failed to load {existing_path}: {e}")
            continue

        edit_instruction = f"Update this object in response to the new object ({new_urlid}) added with behavior: {object_prompt}"
        prompt = (
            f"The current object is: {original_data.get('object_name', original_data.get('object', 'Unknown'))} (don't change it)\n\n"
            f"Original Lua Code:\n{original_data.get('lua_code', '')}\n\n"
            f"Original Particle Effects:\n{json.dumps(original_data.get('particle_json', []), indent=2)}\n\n"
            f"Edit Instruction:\n{edit_instruction}"
        )
        full_prompt = prompt_template + "\n\n" + prompt
        result = call_openai(full_prompt)

        try:
            parsed = json.loads(result)
            # Preserve object_name and overwrite created_at
            original_name = original_data.get("object_name", original_data.get("object", "Unknown"))
            parsed["object_name"] = original_name
            parsed.pop("object", None)
            parsed["created_at"] = datetime.utcnow().isoformat()
            with open(existing_path, 'w', encoding='utf-8') as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
            print(f"[+] Updated: {existing_path}")
        except Exception as e:
            print(f"[Error] Failed to parse or write updated JSON for {obj_id}: {e}")

# --------- Vision Mode ---------
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

    # Overwrite created_at with current system time (if JSON parsable)
    try:
        parsed = json.loads(result)
        parsed["created_at"] = datetime.utcnow().isoformat()
        result = json.dumps(parsed, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Warning] vision-generate could not parse JSON to set created_at: {e}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f"[] Saved to {output_path}")
    return result

# =====================================================================
#                     Error Regeneration Mode
# =====================================================================

def _dynamic_json_path(urlid, root="objects"):
    folder = os.path.join(root, urlid)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{urlid}_DynamicCoding.json")

def _read_dynamic_json(urlid, root="objects"):
    path = _dynamic_json_path(urlid, root)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dynamic JSON not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path

def _backup_file(path):
    if not os.path.exists(path):
        return None
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_path = f"{path}.bak.{ts}"
    with open(path, "rb") as src, open(backup_path, "wb") as dst:
        dst.write(src.read())
    return backup_path

def _write_dynamic_json(urlid, data, root="objects"):
    # Always set created_at to current system UTC time
    data["created_at"] = datetime.utcnow().isoformat()
    path = _dynamic_json_path(urlid, root)
    backup = _backup_file(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path, backup

def _ensure_json_valid(json_text):
    try:
        obj = json.loads(json_text)
    except Exception as e:
        raise ValueError(f"Model did not return valid JSON. Parse error: {e}\nRaw text:\n{json_text}")

    # Accept either object_name or object
    has_name = ("object_name" in obj) or ("object" in obj)
    if not has_name:
        raise ValueError("Missing required key 'object_name' (or legacy 'object') in model output.")

    if "particle_json" not in obj or not isinstance(obj["particle_json"], list):
        raise ValueError("particle_json must be present and a list.")

    # Normalize to object_name for downstream consistency
    if "object_name" not in obj and "object" in obj:
        obj["object_name"] = obj["object"]

    return obj

def _build_error_regen_prompt(existing_json_obj, error_text):
    rules = [
        "Return ONLY a valid JSON object. No markdown, no code fences, no commentary.",
        "Top-level keys must include: \"object_name\" (or \"object\"), \"lua_code\", and \"particle_json\".",
        "If the result is a particle-only effect, ensure 'object_name' contains '@Effect'.",
        "Fix nil references: initialize proxies in start() and guard their usage.",
        "If collisions activate an effect, ensure that effect exists in particle_json.",
        "Keep names consistent; avoid introducing external dependencies.",
        "Ensure the JSON parses with standard json.loads."
    ]
    prompt = f"""
Existing Dynamic JSON (to fix):
{json.dumps(existing_json_obj, ensure_ascii=False, indent=2)}

Error Description / Traceback:
{error_text}

Strict Rules:
- {rules[0]}
- {rules[1]}
- {rules[2]}
- {rules[3]}
- {rules[4]}
- {rules[5]}
- {rules[6]}

Task:
Produce a corrected JSON that resolves the error while preserving intent. If any referenced object or proxy might be nil, add safe initialization and checks. Also ensure any effect triggered in code exists in particle_json.
""".strip()
    return prompt

def regenerate_from_error(urlid, error_text, root="objects", model=None):
    existing_json, in_path = _read_dynamic_json(urlid, root)
    prompt = _build_error_regen_prompt(existing_json, error_text)
    result_text = call_openai(prompt) if model is None else call_openai(prompt)
    fixed_obj = _ensure_json_valid(result_text)

    # Preserve original object_name
    original_name = existing_json.get("object_name", existing_json.get("object", "Unknown"))
    fixed_obj["object_name"] = original_name
    fixed_obj.pop("object", None)

    out_path, backup = _write_dynamic_json(urlid, fixed_obj, root=root)
    print("[] Regeneration complete.")
    print(f"URLID: {urlid}")
    print(f"Input: {in_path}")
    if backup:
        print(f"Backup: {backup}")
    print(f"Output: {out_path}")

# =====================================================================
#   Modify-mode particle preservation & auto-generation helpers
# =====================================================================

def _extract_effect_names(text):
    """Find effect names referenced in Lua or prompt."""
    if not text:
        return set()
    names = set()
    # activateEffect("Name")
    for m in re.findall(r'activateEffect\(\s*"([^"]+)"\s*\)', text):
        names.add(m.strip())
    # effect (dropdown: [Explosion, Smoke]) or effect: [Explosion, Smoke]
    for m in re.findall(r'effect\s*(?:\(dropdown:\s*)?\[\s*([^\]]+?)\s*\]', text, flags=re.IGNORECASE):
        for n in m.split(","):
            n = n.strip().strip('"').strip("'")
            if n:
                names.add(n)
    return names

def _default_particle(name):
    """A minimal, sane particle definition."""
    return {
        "effectName": name,
        "duration": 2.0,
        "startColor": "Color(1, 1, 1, 1)",
        "startSize": 1.0,
        "startSpeed": 1.0,
        "maxParticles": 100,
        "shape": "cone",
        "emissionRate": 10,
        "lifetime": 1.0
    }

def _ensure_particles_consistency(original_data, parsed, object_prompt):
    """Ensure particle_json exists and includes all effects referenced by Lua/prompt.
       - If model omitted particle_json, copy from original.
       - If effects are referenced but missing, add default stubs.
       - If an effect exists in original, prefer its settings over defaults.
    """
    orig_particles = original_data.get("particle_json", []) or []
    parsed_particles = parsed.get("particle_json", [])
    if not isinstance(parsed_particles, list):
        parsed_particles = []

    # Start with model output (if any), else original
    name_to_particle = {}
    for p in parsed_particles:
        if isinstance(p, dict) and "effectName" in p:
            name_to_particle[p["effectName"]] = p

    # Required effect names from Lua + prompt
    needed = set()
    needed |= _extract_effect_names(parsed.get("lua_code", ""))
    needed |= _extract_effect_names(object_prompt)

    # Also include any effects already present in original if model dropped them
    for op in orig_particles:
        nm = op.get("effectName")
        if nm:
            needed.add(nm)

    # Fill missing by copying from original first, otherwise default stub
    orig_map = {p.get("effectName"): p for p in orig_particles if isinstance(p, dict)}
    for nm in needed:
        if nm in name_to_particle:
            continue
        if nm in orig_map:
            name_to_particle[nm] = orig_map[nm]
        else:
            name_to_particle[nm] = _default_particle(nm)

    # Write back
    parsed["particle_json"] = list(name_to_particle.values())

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

    # ---- error mode ----
    error_parser = subparsers.add_parser("error")
    error_parser.add_argument("urlid", help="URLID of the DynamicCoding.json to repair.")
    group = error_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--error-text", help="Inline error description / traceback.")
    group.add_argument("--error-file", help="Path to a text file containing the error.")
    error_parser.add_argument("--root", default="objects", help="Root folder for objects. Default: objects")

    args = parser.parse_args()

    if args.mode == "generate":
        scene = load_scene_session(args.scene_json)
        folder = os.path.join("objects", args.urlid)
        os.makedirs(folder, exist_ok=True)
        existing = load_existing_generated_objects(folder)
        base = load_base_prompt_template_yaml(args.prompt_yaml)
        full_prompt = build_prompt(scene, existing, base, args.object_prompt)
        result = call_openai(full_prompt)
        output_path = os.path.join(folder, f"{args.urlid}_DynamicCoding.json")

        # Overwrite created_at with current system time
        try:
            parsed = json.loads(result)
            parsed["created_at"] = datetime.utcnow().isoformat()
            result = json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Warning] generate could not parse JSON to set created_at: {e}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"[] Generated: {output_path}")

        if args.update_others:
            update_other_virtual_objects(scene, args.urlid, base, args.object_prompt)

    elif args.mode == "modify":
        with open(args.existing_json, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        base_prompt = load_base_prompt_template_yaml(args.prompt_yaml)
        prompt = (
            f"The current object is: {original_data.get('object_name', original_data.get('object', 'Unknown'))} (don't change it)\n\n"
            f"Original Lua Code:\n{original_data.get('lua_code', '')}\n\n"
            f"Original Particle Effects:\n{json.dumps(original_data.get('particle_json', []), indent=2)}\n\n"
            f"Edit Instruction:\n{args.object_prompt.strip()}"
        )
        full_prompt = base_prompt + "\n\n" + prompt
        result = call_openai(full_prompt)

        # Overwrite created_at, PRESERVE object_name, and ensure particles exist
        try:
            parsed = json.loads(result)

            # Lock the name
            original_name = original_data.get("object_name", original_data.get("object", "Unknown"))
            parsed["object_name"] = original_name
            parsed.pop("object", None)

            # Ensure particles are present and complete
            _ensure_particles_consistency(original_data, parsed, args.object_prompt)

            # Timestamp
            parsed["created_at"] = datetime.utcnow().isoformat()
            result = json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Warning] modify could not finalize JSON (created_at/name/particles): {e}")

        with open(args.existing_json, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"[] Modified: {args.existing_json}")

        if args.update_others:
            # Try to guess scene path from existing_json
            urlid = os.path.basename(args.existing_json).split('_')[0]
            scene_path = os.path.join("sessions", f"{urlid}_scene.json")
            if os.path.exists(scene_path):
                scene = load_scene_session(scene_path)
                update_other_virtual_objects(scene, urlid, base_prompt, args.object_prompt)

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

            # Overwrite created_at before writing
            try:
                parsed = json.loads(result)
                parsed["created_at"] = datetime.utcnow().isoformat()
                result = json.dumps(parsed, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[Warning] vision could not parse JSON to set created_at: {e}")

            with open(os.path.join(folder, f"{args.urlid}_DynamicCoding.json"), 'w', encoding='utf-8') as f:
                f.write(result)
        else:
            print(extract_formula_from_image(args.image_path, args.prompt))

    elif args.mode == "vision-generate":
        vision_only_generate(args.image_path, args.urlid)

    elif args.mode == "error":
        if getattr(args, "error_file", None):
            if not os.path.exists(args.error_file):
                raise FileNotFoundError(f"Error file not found: {args.error_file}")
            with open(args.error_file, "r", encoding="utf-8") as f:
                err_text = f.read()
        else:
            err_text = args.error_text
        regenerate_from_error(args.urlid, err_text, root=args.root)

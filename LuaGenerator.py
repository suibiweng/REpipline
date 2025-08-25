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
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a Lua generation agent for Unity simulation. Return ONLY valid JSON if asked to output JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5
    )
    return response.choices[0].message.content

# =====================================================================
#   JSON coercion utilities (handle explanations, code fences, etc.)
# =====================================================================

_FENCE_RE = re.compile(r"```+([a-zA-Z0-9_-]+)?\s*([\s\S]*?)```+", re.MULTILINE)

def _strip_code_fences(text):
    """
    If the whole content is wrapped in a code fence, return inner.
    Otherwise, replace fenced regions with their inner text.
    """
    m = _FENCE_RE.fullmatch(text.strip())
    if m:
        return m.group(2).strip()
    return _FENCE_RE.sub(lambda mm: mm.group(2), text)

def _extract_json_object(text):
    """
    Extract the first balanced top-level JSON object substring from text.
    Raises ValueError if not found.
    """
    s = text.strip()
    start = None
    depth = 0
    in_str = False
    esc = False

    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
                continue
            if ch == '}':
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start is not None:
                        return s[start:i+1]
    raise ValueError("No JSON object found in text.")

def _load_model_json_or_raise(raw_text):
    """
    Try hard to load a JSON object from model output:
      1) direct json.loads
      2) strip code fences, retry
      3) extract first balanced { ... } object, json.loads
    Raises ValueError if all fail.
    """
    try:
        return json.loads(raw_text)
    except Exception:
        pass

    stripped = _strip_code_fences(raw_text)
    if stripped != raw_text:
        try:
            return json.loads(stripped)
        except Exception:
            pass

    try:
        obj_text = _extract_json_object(stripped)
        return json.loads(obj_text)
    except Exception:
        pass

    raise ValueError("Model did not return valid JSON (after fence stripping and extraction).")

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
            parsed = _load_model_json_or_raise(result)
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
        parsed = _load_model_json_or_raise(result)
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
    """
    Validate and normalize model output into a dict.
    Accepts raw text and will coerce/strip to find the JSON object.
    """
    obj = _load_model_json_or_raise(json_text)

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

    # 1st attempt
    result_text = call_openai(prompt) if model is None else call_openai(prompt)
    try:
        fixed_obj = _ensure_json_valid(result_text)
    except Exception:
        # STRICT retry once: ask for JSON ONLY
        strict_prompt = prompt + "\n\nIMPORTANT: Return ONLY a single JSON object. No code fences. No commentary."
        result_text2 = call_openai(strict_prompt)
        fixed_obj = _ensure_json_valid(result_text2)

    # Preserve original object_name and write
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

# =====================================================================
#   Find the correct scene for an object id (current directory only)
# =====================================================================

def find_scene_for_object(obj_id, search_dirs=(".",)):
    """
    Search the given directories (default: current dir) for a scene JSON
    whose generateSpots contains obj_id. Returns (scene_dict, scene_path)
    or (None, None) if not found.

    Looks in:
      - any file ending with _scene.json
      - any .json file (fallback), to catch scenes saved without the suffix
    """
    for d in search_dirs:
        if not os.path.isdir(d):
            continue

        # Prefer *_scene.json files first
        scene_candidates = [n for n in os.listdir(d) if n.endswith("_scene.json")]
        # Fallback to any .json if none matched
        if not scene_candidates:
            scene_candidates = [n for n in os.listdir(d) if n.endswith(".json")]

        for name in scene_candidates:
            path = os.path.join(d, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    scene = json.load(f)
            except Exception:
                continue

            spots = scene.get("generateSpots", []) or []
            for spot in spots:
                if spot.get("id") == obj_id:
                    return scene, path

    return None, None

# =====================================================================
# Name safety & formatting helpers (CONST_CASE + ID guards)
# =====================================================================

ID_PATTERNS = [
    re.compile(r"^\d{8,}$"),                              # pure digits 8+
    re.compile(r"^[0-9a-fA-F]{8,}$"),                     # hex-like 8+
    re.compile(r"^\d{8,}[0-9a-fA-F]{4,}$"),               # timestamp + hex mix
    re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$"),  # UUID
]

def is_id_shaped(s: str) -> bool:
    if s is None:
        return True
    if not isinstance(s, str):
        s = str(s)
    ss = s.strip()
    if not ss:
        return True
    for pat in ID_PATTERNS:
        if pat.match(ss):
            return True
    return False

def noun_phrase_from_prompt(prompt_text: str) -> str:
    if not prompt_text:
        return ""
    t = prompt_text.strip().strip('"').strip("'")
    m = re.search(r'"([^"]{1,64})"', t)
    if m:
        t = m.group(1).strip()
    t = re.split(r'[:\n\r]', t, maxsplit=1)[0].strip()
    words = re.findall(r"[A-Za-z0-9#@\-']+", t)
    if not words:
        return ""
    return " ".join(words[:4])

def noun_phrase_from_comment(comment_text: str) -> str:
    """
    Try to extract a short noun phrase (<=4 words) from comment.
    Prefer quoted spans or the first bolded/colored token; else first 1–4 words.
    """
    if not isinstance(comment_text, str) or not comment_text.strip():
        return ""
    t = comment_text.strip()

    # quoted span first
    m = re.search(r'"([^"]{1,64})"', t)
    if m:
        s = " ".join(re.findall(r"[A-Za-z0-9#@\-']+", m.group(1)))
        return s[:64].strip()

    # HTML-like tags <b><color=...>Name</color></b>
    m = re.search(r">([^<>]{1,64})<", t)
    if m:
        cand = " ".join(re.findall(r"[A-Za-z0-9#@\-']+", m.group(1)))
        if cand:
            return " ".join(cand.split()[:4])

    # fallback: first 1–4 words
    words = re.findall(r"[A-Za-z0-9#@\-']+", t)
    return " ".join(words[:4]) if words else ""

def collect_known_ids(scene_json: dict) -> set:
    ids = set()
    for so in scene_json.get("SceneObjects", []) or []:
        if isinstance(so, dict) and so.get("id"):
            ids.add(str(so["id"]))
    for gs in scene_json.get("generateSpots", []) or []:
        if isinstance(gs, dict) and gs.get("id"):
            ids.add(str(gs["id"]))
    if scene_json.get("sessionURLID"):
        ids.add(str(scene_json["sessionURLID"]))
    return ids

def to_const_case(name: str) -> str:
    """
    Convert a string to UPPERCASE_WITH_UNDERSCORES.
    Collapses whitespace to single underscore, trims, and uppercases.
    """
    if not isinstance(name, str):
        name = str(name) if name is not None else ""
    s = re.sub(r"\s+", "_", name.strip())
    return s.upper()

def best_name_from_scene_or_prompt(scene_json: dict, prompt_text: str, comment_text: str = "") -> str:
    # Real-object explicit tag
    if isinstance(prompt_text, str) and prompt_text.strip().startswith("[This is a real object in the space]"):
        real = prompt_text.split("]", 1)[-1].strip()
        names = [so.get("name", "") for so in (scene_json.get("SceneObjects") or []) if isinstance(so, dict)]
        for n in names:
            if n and n.lower() == real.lower():
                return n

    # generateSpots gameObjectName semantic match
    gspots = scene_json.get("generateSpots") or []
    pt = (prompt_text or "").strip().lower()
    for gs in gspots:
        gon = (gs.get("gameObjectName") or "").strip()
        if gon and (gon.lower() == pt or gon.lower() in pt or pt in gon.lower()):
            return gon

    # try comment-derived noun phrase
    cnp = noun_phrase_from_comment(comment_text or "")
    if cnp:
        return cnp

    # fallback: noun phrase from prompt
    np = noun_phrase_from_prompt(prompt_text or "")
    return np or "Object"

def purge_ids_from_payload(obj: dict, known_ids: set, safe_name: str) -> None:
    code = obj.get("lua_code")
    if isinstance(code, str) and known_ids:
        for tid in known_ids:
            if not tid:
                continue
            code = code.replace(f'"{tid}"', f'"{safe_name}"')
            code = code.replace(f"'{tid}'", f"'{safe_name}'")
        obj["lua_code"] = code
    for key in ("param_ui_lua", "param_ui_particle"):
        arr = obj.get(key)
        if isinstance(arr, list):
            for it in arr:
                if isinstance(it, dict) and isinstance(it.get("options"), list):
                    it["options"] = [safe_name if (isinstance(x, str) and x in known_ids) else x for x in it["options"]]

def request_name_only_with_openai(base_template: str, scene_json: dict, object_prompt: str, bad_name: str, comment_text: str = "") -> str:
    scene_objects_entries = ", ".join(json.dumps(x, ensure_ascii=False) for x in (scene_json.get("SceneObjects") or []))
    generate_spots_entries = ", ".join(json.dumps(x, ensure_ascii=False) for x in (scene_json.get("generateSpots") or []))
    narrow_instruction = f"""
You produced an invalid object name: "{bad_name}".
Using ONLY these sources (in order): SceneObjects[].name, generateSpots[].gameObjectName, a noun phrase from the user prompt, or a noun phrase already present in your own 'comment' text,
return a STRICT JSON object with just one field: "object_name".
Rules:
- Never return any id/sessionURLID/UUID/timestamp-like token.
- Preserve multi-word names (e.g., "Baseball Bat" must remain multi-word).
- Do NOT add numbering or suffixes.
- Return ONLY: {{"object_name":"..."}}

Context:
"SceneObjects": [{scene_objects_entries}]
"generateSpots": [{generate_spots_entries}]
User prompt: {object_prompt.strip()}
Comment (may already describe the object): {comment_text.strip() if isinstance(comment_text, str) else ""}
""".strip()
    strict_prompt = base_template + "\n\n" + narrow_instruction
    raw = call_openai(strict_prompt)
    try:
        data = _load_model_json_or_raise(raw)
        name = data.get("object_name", "")
        if isinstance(name, str):
            return name.strip()
    except Exception:
        pass
    return best_name_from_scene_or_prompt(scene_json, object_prompt, comment_text)

# =====================================================================
# Diagnostics helper for missing modify file
# =====================================================================

def _diagnose_missing_existing_json(path_candidate: str):
    norm = os.path.normpath(path_candidate)
    print(f"[Modify] File not found: {norm}")
    folder = os.path.dirname(norm)
    print(f"[Modify] Expected folder: {folder}")
    if not os.path.isdir(folder):
        print("[Modify] Folder does not exist.")
        # Try to guess urlid and show suggestions from objects/
        m = re.search(r"[\\/](objects)[\\/]([^\\/]+)", norm)
        if m:
            urlid = m.group(2)
            # objects directory relative to CWD
            obj_root = "objects"
            if os.path.isdir(obj_root):
                possible = []
                for d in os.listdir(obj_root):
                    if urlid in d:
                        sub = os.path.join(obj_root, d)
                        if os.path.isdir(sub):
                            for fn in os.listdir(sub):
                                if fn.endswith("_DynamicCoding.json"):
                                    possible.append(os.path.join(sub, fn))
                if possible:
                    print("[Modify] Possible existing files:")
                    for p in possible:
                        print(" -", os.path.normpath(p))
            else:
                print("[Modify] 'objects' directory not found in current working directory.")
        return

    print("[Modify] Folder exists. Listing *_DynamicCoding.json files:")
    try:
        matches = [fn for fn in os.listdir(folder) if fn.endswith("_DynamicCoding.json")]
        if matches:
            for fn in matches:
                print(" -", os.path.normpath(os.path.join(folder, fn)))
        else:
            print(" (none)")
    except Exception as e:
        print(f"[Modify] Could not list folder contents: {e}")

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
            parsed = _load_model_json_or_raise(result)

            # Name repair before we dump to disk
            known_ids = collect_known_ids(scene)
            comment_hint = parsed.get("comment", "")

            name = parsed.get("object_name") or parsed.get("object") or ""
            bad = is_id_shaped(name) or (name in known_ids) or (not isinstance(name, str) or not name.strip())
            if bad:
                base_template = load_base_prompt_template_yaml(args.prompt_yaml)
                fixed = request_name_only_with_openai(base_template, scene, args.object_prompt, name or "<empty>", comment_hint)
                if not fixed or is_id_shaped(fixed) or fixed in known_ids:
                    fixed = best_name_from_scene_or_prompt(scene, args.object_prompt, comment_hint)
                fixed = to_const_case(fixed)
                parsed["object_name"] = fixed
                parsed.pop("object", None)
            else:
                fixed = to_const_case(name)
                parsed["object_name"] = fixed
                parsed.pop("object", None)

            purge_ids_from_payload(parsed, known_ids, parsed["object_name"])

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
        target_path = os.path.normpath(args.existing_json)

        # Helpful diagnostics BEFORE attempting to open
        if not os.path.exists(target_path):
            _diagnose_missing_existing_json(target_path)
            # Exit with a clear message
            raise FileNotFoundError(f"[Modify] Cannot proceed. File not found: {target_path}")

        with open(target_path, 'r', encoding='utf-8') as f:
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

        # Overwrite created_at, PRESERVE object_name, ensure particles, and coerce JSON
        try:
            parsed = _load_model_json_or_raise(result)

            # Lock the name (then repair if it was ID-shaped)
            original_name = original_data.get("object_name", original_data.get("object", "Unknown"))
            parsed["object_name"] = original_name
            parsed.pop("object", None)

            # Ensure particles are present and complete
            _ensure_particles_consistency(original_data, parsed, args.object_prompt)

            # If original name was ID-ish, repair now (using comment as hint)
            try:
                obj_id = os.path.basename(target_path).split('_')[0]
                scene_guess, _ = find_scene_for_object(obj_id, search_dirs=(".",))
            except Exception:
                scene_guess = None
            if not scene_guess:
                scene_guess = {"SceneObjects": [], "generateSpots": []}

            known_ids_mod = collect_known_ids(scene_guess)
            comment_hint_mod = parsed.get("comment", "")

            current_name = parsed["object_name"]
            if is_id_shaped(current_name) or current_name in known_ids_mod or not str(current_name).strip():
                base_template = load_base_prompt_template_yaml(args.prompt_yaml)
                repaired = request_name_only_with_openai(base_template, scene_guess, args.object_prompt, current_name, comment_hint_mod)
                if not repaired or is_id_shaped(repaired) or repaired in known_ids_mod:
                    repaired = best_name_from_scene_or_prompt(scene_guess, args.object_prompt, comment_hint_mod)
                repaired = to_const_case(repaired)
                parsed["object_name"] = repaired
            else:
                # enforce CONST-CASE even for good names
                repaired = to_const_case(current_name)
                parsed["object_name"] = repaired

            purge_ids_from_payload(parsed, known_ids_mod, parsed["object_name"])

            # Timestamp
            parsed["created_at"] = datetime.utcnow().isoformat()
            result = json.dumps(parsed, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Warning] modify could not finalize JSON (created_at/name/particles): {e}")

        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"[] Modified: {target_path}")

        if args.update_others:
            # Find the correct scene by scanning the current directory for this object id
            obj_id = os.path.basename(target_path).split('_')[0]
            scene, scene_path = find_scene_for_object(obj_id, search_dirs=(".",))
            if scene:
                update_other_virtual_objects(scene, obj_id, base_prompt, args.object_prompt)
            else:
                print(f"[Skip] Could not find a scene containing object id {obj_id} in current directory '.'.")

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
                parsed = _load_model_json_or_raise(result)
                # Name safety (use comment as hint + CONST-CASE)
                known_ids_v = collect_known_ids(scene)
                comment_hint_v = parsed.get("comment", "")
                nm = parsed.get("object_name") or parsed.get("object") or ""
                if is_id_shaped(nm) or nm in known_ids_v or not str(nm).strip():
                    base_template = load_base_prompt_template_yaml(args.prompt_yaml)
                    fixed = request_name_only_with_openai(base_template, scene, object_prompt, nm or "<empty>", comment_hint_v)
                    if not fixed or is_id_shaped(fixed) or fixed in known_ids_v:
                        fixed = best_name_from_scene_or_prompt(scene, object_prompt, comment_hint_v)
                    parsed["object_name"] = to_const_case(fixed)
                    parsed.pop("object", None)
                else:
                    parsed["object_name"] = to_const_case(nm)
                    parsed.pop("object", None)
                purge_ids_from_payload(parsed, known_ids_v, parsed["object_name"])

                parsed["created_at"] = datetime.utcnow().isoformat()
                result = json.dumps(parsed, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[Warning] vision could not parse JSON to set created_at: {e}")

            out_file = os.path.join(folder, f"{args.urlid}_DynamicCoding.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"[] Saved: {out_file}")
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

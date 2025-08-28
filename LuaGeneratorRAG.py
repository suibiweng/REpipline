import os
import re
import json
import yaml
import faiss
import argparse
import numpy as np
from datetime import datetime
from typing import Any, Dict, List, Tuple

# ===========================
# OpenAI client / API key
# ===========================
try:
    # Prefer config.json next to this file; fallback to CWD
    HERE = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(HERE, "config.json")
    if not os.path.exists(cfg_path):
        cfg_path = "config.json"
    with open(cfg_path, "r", encoding="utf-8") as _f:
        _api_key = json.load(_f)["open_ai_key"]
except Exception as _e:
    raise RuntimeError("Unable to read OpenAI key from config.json") from _e

import openai
client = openai.OpenAI(api_key=_api_key)

# ===========================
# Env flags / directories
# ===========================
RAG_ROOT = os.getenv("LUA_RAG_ROOT", os.path.join(HERE, "rag_index"))
PRUNE_MISSING = os.getenv("LUA_RAG_PRUNE_MISSING", "0") == "1"
DISABLE_GUIDES = os.getenv("LUA_RAG_DISABLE_GUIDES", "0") == "1"
UPDATE_OTHERS = os.getenv("LUA_RAG_UPDATE_OTHERS", "0") == "1"
ERROR_ROUNDS = int(os.getenv("LUA_RAG_ERROR_ROUNDS", "2"))

GUIDES_DIR = os.path.join(HERE, "rag_guides")
OBJECTS_DIR = os.path.join(HERE, "objects")

os.makedirs(RAG_ROOT, exist_ok=True)
os.makedirs(OBJECTS_DIR, exist_ok=True)

# ===========================
# RAG: FAISS + storage
# ===========================
EMBED_MODEL = "text-embedding-3-large"
EMBED_DIM = 3072

INDEX_FILE = os.path.join(RAG_ROOT, "scene_index.faiss")
DOCS_FILE = os.path.join(RAG_ROOT, "docs.json")

if os.path.exists(INDEX_FILE) and os.path.exists(DOCS_FILE):
    index = faiss.read_index(INDEX_FILE)
    with open(DOCS_FILE, "r", encoding="utf-8") as f:
        docs: List[Dict[str, Any]] = json.load(f)
else:
    index = faiss.IndexFlatL2(EMBED_DIM)
    docs = []

def _save_index():
    faiss.write_index(index, INDEX_FILE)
    with open(DOCS_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

def _embed(text: str) -> np.ndarray:
    if not isinstance(text, str) or not text.strip():
        return np.zeros(EMBED_DIM, dtype="float32")
    resp = client.embeddings.create(model=EMBED_MODEL, input=text)
    return np.array(resp.data[0].embedding, dtype="float32")

def rag_add(text: str, metadata: Dict[str, Any]):
    vec = _embed(text)
    index.add(np.array([vec]))
    docs.append({"text": text, "metadata": metadata})
    _save_index()

def rag_search(query: str, k: int = 5) -> List[Dict[str, Any]]:
    if not docs:
        return []
    qv = _embed(query)
    D, I = index.search(np.array([qv]), k)
    out: List[Dict[str, Any]] = []
    for i in I[0]:
        if 0 <= int(i) < len(docs):
            out.append(docs[int(i)])
    return out

def rag_upsert(text: str, metadata: Dict[str, Any], key: Tuple[str, ...] = ("type","source")):
    """Replace any existing doc with the same key tuple, then rebuild FAISS."""
    global index, docs
    ktuple = tuple(metadata.get(k) for k in key)
    kept: List[Dict[str, Any]] = []
    for d in docs:
        mk = tuple(d.get("metadata", {}).get(k) for k in key)
        if mk != ktuple:
            kept.append(d)
    vecs = [_embed(d["text"]) for d in kept] if kept else []
    new_index = faiss.IndexFlatL2(EMBED_DIM)
    if vecs:
        new_index.add(np.array(vecs))
    new_index.add(np.array([_embed(text)]))
    kept.append({"text": text, "metadata": metadata})
    index = new_index
    docs  = kept
    _save_index()

def index_guides_if_any(folder: str = GUIDES_DIR):
    if DISABLE_GUIDES:
        return
    if not os.path.isdir(folder):
        return
    have = set(str(d.get("metadata", {}).get("source")) for d in docs if d.get("metadata", {}).get("type") == "guide")
    for fn in os.listdir(folder):
        if not fn.lower().endswith((".md", ".txt")):
            continue
        if fn in have:
            continue
        path = os.path.join(folder, fn)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            rag_add(text, {"type": "guide", "source": fn})
            print(f"[RAG] Indexed guide: {fn}")
        except Exception as e:
            print(f"[RAG] Skipped {fn}: {e}")

# ===========================
# Contract/template loading
# ===========================
def load_base_prompt_template_yaml(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["prompt_template"]

def _clip(txt: str, max_chars: int = 4000) -> str:
    if not isinstance(txt, str):
        return ""
    if len(txt) <= max_chars:
        return txt
    return txt[:max_chars] + "\n…\n[truncated]"

# ===========================
# Name/ID guards
# ===========================
ID_PATS = [
    re.compile(r"^\d{8,}$"),
    re.compile(r"^[0-9a-fA-F]{8,}$"),
    re.compile(r"^\d{8,}[0-9a-fA-F]{4,}$"),
    re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$"),
]

def is_id_shaped(s: Any) -> bool:
    if s is None:
        return True
    if not isinstance(s, str):
        s = str(s)
    ss = s.strip()
    if not ss:
        return True
    for p in ID_PATS:
        if p.match(ss):
            return True
    return False

def collect_known_ids(scene_json: Dict[str, Any]) -> set:
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

def noun_phrase_from_prompt(prompt_text: str) -> str:
    if not prompt_text:
        return ""
    t = prompt_text.strip().strip('"').strip("'")
    m = re.search(r'"([^"\n]{1,64})"', t)
    if m:
        t = m.group(1).strip()
    t = re.split(r"[:\n\r]", t, maxsplit=1)[0].strip()
    words = re.findall(r"[A-Za-z0-9#@\-']+", t)
    return " ".join(words[:4]) if words else ""

def best_name_from_scene_or_prompt(scene_json: Dict[str, Any], object_prompt: str) -> str:
    pt = (object_prompt or "").strip().lower()
    for gs in scene_json.get("generateSpots", []) or []:
        gon = (gs.get("gameObjectName") or "").strip()
        if not gon:
            continue
        gl = gon.lower()
        if gl == pt or gl in pt or pt in gl:
            return gon
    return noun_phrase_from_prompt(object_prompt) or "Object"

# ===========================
# RAG helpers for scene
# ===========================
def _present_ids_from_scene(scene_json: Dict[str, Any]) -> set:
    return set(str(gs.get("id")) for gs in (scene_json.get("generateSpots") or []) if gs.get("id"))

def prune_objects_not_in_current_scene(current_ids: set):
    """Remove generated_object docs whose urlid is not present in the current scene (opt-in)."""
    global index, docs
    if not current_ids:
        return
    keep: List[Dict[str, Any]] = []
    removed = 0
    for d in docs:
        mt = d.get("metadata", {})
        if mt.get("type") == "generated_object":
            uid = str(mt.get("urlid", ""))
            if uid and uid not in current_ids:
                removed += 1
                continue
        keep.append(d)
    if removed == 0:
        return
    vecs = [_embed(d["text"]) for d in keep] if keep else []
    new_index = faiss.IndexFlatL2(EMBED_DIM)
    if vecs:
        new_index.add(np.array(vecs))
    docs = keep
    index = new_index
    _save_index()
    print(f"[RAG] Pruned {removed} stale generated objects not in this scene.")

# ===========================
# Prompt assembly + model call
# ===========================
FENCE_RE = re.compile(r"```+([a-zA-Z0-9_-]+)?\s*([\s\S]*?)```+", re.MULTILINE)

def _strip_code_fences(text: str) -> str:
    s = text.strip()
    m = FENCE_RE.fullmatch(s)
    if m:
        return m.group(2).strip()
    return FENCE_RE.sub(lambda mm: mm.group(2), s)

def _extract_first_json(text: str) -> str:
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

def coerce_json(text: str) -> Dict[str, Any]:
    # Try direct
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try strip fences
    stripped = _strip_code_fences(text)
    try:
        return json.loads(stripped)
    except Exception:
        pass
    # Try balanced-extract
    obj = _extract_first_json(stripped)
    return json.loads(obj)

def call_openai(prompt: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",  # swap to gpt-5 when available
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a STRICT Lua+Particles generator.\n"
                    "Return ONLY a single JSON object. No code fences. No markdown.\n"
                    "Follow the contract in the prompt; choose safe defaults if unknown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content

def build_prompt(scene_json: Dict[str, Any], object_prompt: str, base_template: str, present_ids: set | None = None) -> str:
    premise = scene_json.get("premise", "")
    detail = (scene_json.get("prompt", "") or "").strip()

    # RAG retrieval: oversample then filter out stale generated objects
    queries = [object_prompt]
    if premise:
        queries.append(premise)
    retrieved_texts: List[str] = []
    for q in queries:
        for r in rag_search(q, k=8):
            meta = r.get("metadata", {})
            rtype = meta.get("type", "doc")
            if rtype == "generated_object":
                uid = str(meta.get("urlid", ""))
                if present_ids and (not uid or uid not in present_ids):
                    continue
            tag = f"[{rtype}: {meta.get('source', meta.get('urlid',''))}]"
            retrieved_texts.append(tag + "\n" + _clip(r.get("text", ""), 2500))
    guide_notes = "\n\n".join(retrieved_texts)

    scene_objects = scene_json.get("SceneObjects", []) or []
    generate_spots = scene_json.get("generateSpots", []) or []

    scene_objects_entries = ", ".join(json.dumps(x, ensure_ascii=False) for x in scene_objects)
    generate_spots_entries = ", ".join(json.dumps(x, ensure_ascii=False) for x in generate_spots)

    fields = {
        "premise": premise,
        "prompt": detail,
        "existing_objects": guide_notes,   # inject RAG context here
        "scene_objects": scene_objects_entries,
        "generate_spots": generate_spots_entries,
    }

    # loose replace without template parsing (so braces in contract survive)
    filled = base_template
    for k, v in sorted(fields.items(), key=lambda kv: len(kv[0]), reverse=True):
        filled = filled.replace("{" + k + "}", v)

    if guide_notes:
        filled += "\n\nGuides & Memory (RAG excerpts):\n" + guide_notes

    return f"{filled}\n\nObject Prompt:\n{object_prompt.strip()}"

# ===========================
# Error regeneration helpers
# ===========================
def _dynamic_json_path(urlid: str, root: str = OBJECTS_DIR) -> str:
    folder = os.path.join(root, urlid)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{urlid}_DynamicCoding.json")

def _read_dynamic_json(urlid: str, root: str = OBJECTS_DIR) -> Tuple[Dict[str, Any], str]:
    path = _dynamic_json_path(urlid, root)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dynamic JSON not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f), path

def _write_dynamic_json(urlid: str, data: Dict[str, Any], root: str = OBJECTS_DIR) -> str:
    data["created_at"] = datetime.utcnow().isoformat()
    path = _dynamic_json_path(urlid, root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path

def _build_error_regen_prompt(existing_json_obj: Dict[str, Any], error_text: str) -> str:
    rules = [
        "Return ONLY a valid JSON object. No markdown, no code fences, no commentary.",
        'Top-level keys must include: "object_name" (or "object"), "lua_code", and "particle_json".',
        "If the result is a particle-only effect, ensure 'object_name' contains '@Effect'.",
        "Fix nil references: initialize proxies in start() and guard their usage.",
        "If collisions activate an effect, ensure that effect exists in particle_json.",
        "Keep names consistent; avoid introducing external dependencies.",
        "Ensure the JSON parses with standard json.loads.",
    ]
    prompt = (
        "Existing Dynamic JSON (to fix):\n"
        f"{json.dumps(existing_json_obj, ensure_ascii=False, indent=2)}\n\n"
        "Error Description / Traceback:\n"
        f"{error_text}\n\n"
        "Strict Rules:\n- " + "\n- ".join(rules) + "\n\n"
        "Task:\n"
        "Produce a corrected JSON that resolves the error while preserving intent. "
        "If any referenced object or proxy might be nil, add safe initialization and checks. "
        "Also ensure any effect triggered in code exists in particle_json."
    )
    return prompt

def regenerate_from_error(urlid: str, error_text: str, rounds: int = ERROR_ROUNDS):
    existing_json, in_path = _read_dynamic_json(urlid)
    prompt = _build_error_regen_prompt(existing_json, error_text)

    last_exc = None
    for _ in range(max(1, int(rounds))):
        result_text = call_openai(prompt)
        try:
            fixed_obj = coerce_json(result_text)
        except Exception as e:
            # Retry with stricter instructions once per loop
            strict_prompt = prompt + "\n\nIMPORTANT: Return ONLY a single JSON object. No code fences. No commentary."
            try:
                result_text2 = call_openai(strict_prompt)
                fixed_obj = coerce_json(result_text2)
            except Exception as e2:
                last_exc = e2
                continue

        # Preserve name (lock)
        original_name = existing_json.get("object_name", existing_json.get("object", "Object"))
        fixed_obj["object_name"] = original_name
        fixed_obj.pop("object", None)

        out_path = _write_dynamic_json(urlid, fixed_obj)
        print("[] Regeneration complete.")
        print(f"URLID: {urlid}")
        print(f"Input: {in_path}")
        print(f"Output: {out_path}")

        # Feed back to RAG
        try:
            rag_upsert(json.dumps(fixed_obj, ensure_ascii=False), {"type": "generated_object", "urlid": urlid}, key=("type","urlid"))
        except Exception:
            pass
        return

    if last_exc:
        raise last_exc

# ===========================
# Main generate flow
# ===========================
def repair_object_name(scene: Dict[str, Any], parsed: Dict[str, Any], object_prompt: str) -> None:
    known_ids = collect_known_ids(scene)
    name = parsed.get("object_name") or parsed.get("object") or ""
    bad = is_id_shaped(name) or (name in known_ids) or not str(name).strip()
    if bad:
        fixed = best_name_from_scene_or_prompt(scene, object_prompt)
        if is_id_shaped(fixed) or fixed in known_ids:
            fixed = "Object"
        parsed["object_name"] = fixed
        parsed.pop("object", None)

def main(scene_path: str, prompt_yaml: str, urlid: str, object_prompt: str):
    # 0) Index guides
    index_guides_if_any(GUIDES_DIR)

    # 1) Load scene + contract template
    with open(scene_path, "r", encoding="utf-8") as f:
        scene = json.load(f)
    base_template = load_base_prompt_template_yaml(prompt_yaml)

    # 2) Upsert this scene doc into RAG
    try:
        rag_upsert(json.dumps(scene, ensure_ascii=False), {"type": "scene", "source": os.path.basename(scene_path)}, key=("type","source"))
    except Exception:
        pass

    # 3) Optional prune missing objects from RAG
    present_ids = _present_ids_from_scene(scene)
    if PRUNE_MISSING:
        prune_objects_not_in_current_scene(present_ids)

    # 4) Build prompt and call model
    full_prompt = build_prompt(scene, object_prompt, base_template, present_ids)
    raw = call_openai(full_prompt)

    # 5) Coerce JSON; retry once in strict mode if needed
    try:
        parsed = coerce_json(raw)
    except Exception:
        strict = full_prompt + "\n\nIMPORTANT: Return ONLY a single JSON object. No code fences."
        raw2 = call_openai(strict)
        parsed = coerce_json(raw2)

    # 6) Name/ID safety
    repair_object_name(scene, parsed, object_prompt)

    # 7) Timestamp and persist
    parsed["created_at"] = datetime.utcnow().isoformat()
    out_dir = os.path.join(OBJECTS_DIR, urlid)
    os.makedirs(out_dir, exist_ok=True)
    output_path = os.path.join(out_dir, f"{urlid}_DynamicCoding.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    print(f"[+] Generated and saved: {output_path}")

    # 8) Feed the final JSON back into RAG
    try:
        rag_upsert(json.dumps(parsed, ensure_ascii=False), {"type": "generated_object", "urlid": urlid}, key=("type","urlid"))
    except Exception:
        pass

    # 9) Optional peer cascade
    _update_peers_if_requested(scene, urlid, base_template, object_prompt)

def _update_peers_if_requested(scene: Dict[str, Any], new_urlid: str, base_template: str, object_prompt: str):
    if not UPDATE_OTHERS:
        return
    spots = scene.get("generateSpots") or []
    present_ids = _present_ids_from_scene(scene)

    for spot in spots:
        other_id = str(spot.get("id") or "")
        if not other_id or other_id == new_urlid:
            continue

        existing_path = os.path.join(OBJECTS_DIR, other_id, f"{other_id}_DynamicCoding.json")
        if not os.path.exists(existing_path):
            # Only update peers that already exist
            continue

        try:
            with open(existing_path, "r", encoding="utf-8") as f:
                original = json.load(f)
        except Exception:
            continue

        keep_name = original.get("object_name") or original.get("object") or "Object"
        original_lua = original.get("lua_code", "")
        original_particles = original.get("particle_json", [])

        peer_instruction = (
            "[PEER CASCADE]\n"
            f"Do NOT change object_name; keep it EXACTLY: {keep_name}\n\n"
            "Original Lua Code:\n"
            f"{original_lua}\n\n"
            "Original Particle Effects:\n"
            f"{json.dumps(original_particles, ensure_ascii=False)}\n\n"
            "Edit Instruction:\n"
            f"Update behavior in response to changes in object '{new_urlid}'.\n"
            f"User instruction:\n{object_prompt}"
        )

        full_prompt = build_prompt(scene, peer_instruction, base_template, present_ids)
        raw = call_openai(full_prompt)
        try:
            parsed = coerce_json(raw)
        except Exception:
            strict = full_prompt + "\n\nIMPORTANT: Return ONLY a single JSON object. No code fences."
            parsed = coerce_json(call_openai(strict))

        parsed["object_name"] = keep_name  # lock name
        parsed.pop("object", None)
        parsed["created_at"] = datetime.utcnow().isoformat()

        os.makedirs(os.path.dirname(existing_path), exist_ok=True)
        with open(existing_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)

        try:
            rag_upsert(json.dumps(parsed, ensure_ascii=False), {"type": "generated_object", "urlid": other_id}, key=("type","urlid"))
        except Exception:
            pass

        print(f"[cascade] Updated peer: {existing_path}")

# ===========================
# CLI
# ===========================
def _parse_args():
    ap = argparse.ArgumentParser(description="RAG-enabled Lua generator")
    ap.add_argument("--error", action="store_true", help="enter error repair mode")

    # In generate mode we require 4 positionals
    # In error mode we require 2 positionals
    ap.add_argument("p1")
    ap.add_argument("p2", nargs="?")
    ap.add_argument("p3", nargs="?")
    ap.add_argument("p4", nargs="?")
    return ap.parse_args()

if __name__ == "__main__":
    args = _parse_args()

    if args.error:
        # args: --error <urlid> <error_text>
        urlid = args.p1
        error_text = args.p2 or ""
        try:
            regenerate_from_error(urlid, error_text, rounds=ERROR_ROUNDS)
        except Exception as e:
            print("[error] repair failed:", e)
            raise
    else:
        # args: <scene_json> <yaml_path> <urlid> <object_prompt>
        scene_json = args.p1
        yaml_path = args.p2
        urlid = args.p3
        object_prompt = args.p4

        if not (scene_json and yaml_path and urlid and object_prompt):
            raise ValueError("Usage: python LuaGeneratorRAG.py <scene_json> <yaml_path> <urlid> <object_prompt>")

        try:
            main(scene_json, yaml_path, urlid, object_prompt)
        except Exception as e:
            print("[error] generate failed:", e)
            raise

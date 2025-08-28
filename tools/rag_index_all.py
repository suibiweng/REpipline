import argparse, glob, json, os
from typing import Dict, Any, List, Tuple

import faiss
import numpy as np
import openai

# ---- Config / Paths ----
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(PROJECT_ROOT)  # project root (one level up from tools/)

CONFIG_PATH = os.path.join(ROOT, "config.json")
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    API_KEY = json.load(f)["open_ai_key"]

client = openai.OpenAI(api_key=API_KEY)

EMBED_MODEL = "text-embedding-3-large"
EMBED_DIM   = 3072

RAG_DIR   = os.getenv("LUA_RAG_ROOT", os.path.join(ROOT, "rag_index"))
INDEX_FILE = os.path.join(RAG_DIR, "scene_index.faiss")
DOCS_FILE  = os.path.join(RAG_DIR, "docs.json")

GUIDES_DIR  = os.path.join(ROOT, "rag_guides")
SCENES_DIR  = ROOT
OBJECTS_DIR = os.path.join(ROOT, "objects")

os.makedirs(RAG_DIR, exist_ok=True)

# ---- Storage ----
if os.path.exists(INDEX_FILE) and os.path.exists(DOCS_FILE):
    index = faiss.read_index(INDEX_FILE)
    with open(DOCS_FILE, "r", encoding="utf-8") as f:
        docs: List[Dict[str, Any]] = json.load(f)
else:
    index = faiss.IndexFlatL2(EMBED_DIM)
    docs = []


def _save():
    faiss.write_index(index, INDEX_FILE)
    with open(DOCS_FILE, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


def _embed(text: str) -> np.ndarray:
    if not isinstance(text, str) or not text.strip():
        return np.zeros(EMBED_DIM, dtype="float32")
    resp = client.embeddings.create(model=EMBED_MODEL, input=text)
    return np.array(resp.data[0].embedding, dtype="float32")


def _rebuild_with(kept: List[Dict[str, Any]]):
    global index, docs
    vecs = [_embed(d["text"]) for d in kept] if kept else []
    new_index = faiss.IndexFlatL2(EMBED_DIM)
    if vecs:
        new_index.add(np.array(vecs))
    docs = list(kept)
    index = new_index


def upsert(text: str, metadata: Dict[str, Any], key: Tuple[str, ...]):
    ktuple = tuple(metadata.get(k) for k in key)
    kept = []
    for d in docs:
        mk = tuple(d.get("metadata", {}).get(k) for k in key)
        if mk != ktuple:
            kept.append(d)
    kept.append({"text": text, "metadata": metadata})
    _rebuild_with(kept)


# ---- Indexers ----

def index_guides(folder: str) -> int:
    if not os.path.isdir(folder):
        return 0
    have = set(str(d.get("metadata", {}).get("source")) for d in docs if d.get("metadata", {}).get("type") == "guide")
    cnt = 0
    for fn in os.listdir(folder):
        if not fn.lower().endswith((".md", ".txt")):
            continue
        if fn in have:
            continue
        path = os.path.join(folder, fn)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            upsert(text, {"type": "guide", "source": fn}, key=("type","source"))
            cnt += 1
        except Exception:
            pass
    return cnt


def index_scenes(folder: str) -> int:
    pattern1 = os.path.join(folder, "*_scene.json")
    pattern2 = os.path.join(folder, "*scene.json")
    files = sorted(set(glob.glob(pattern1)) | set(glob.glob(pattern2)))
    cnt = 0
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            upsert(json.dumps(data, ensure_ascii=False), {"type": "scene", "source": os.path.basename(fp)}, key=("type","source"))
            cnt += 1
        except Exception:
            pass
    return cnt


def index_objects(folder: str) -> int:
    if not os.path.isdir(folder):
        return 0
    files = glob.glob(os.path.join(folder, "*", "*_DynamicCoding.json"))
    cnt = 0
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            # urlid from folder or filename prefix
            urlid = os.path.basename(fp).split("_")[0]
            folder_id = os.path.basename(os.path.dirname(fp))
            if not urlid:
                urlid = folder_id
            upsert(json.dumps(data, ensure_ascii=False), {"type": "generated_object", "urlid": urlid}, key=("type","urlid"))
            cnt += 1
        except Exception:
            pass
    return cnt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--guides-dir", default=GUIDES_DIR)
    ap.add_argument("--scenes-dir", default=SCENES_DIR)
    ap.add_argument("--objects-dir", default=OBJECTS_DIR)
    ap.add_argument("--skip-guides", action="store_true")
    ap.add_argument("--include-objects", action="store_true")
    ap.add_argument("--reset", action="store_true", help="start fresh index (clears rag_index)")
    args = ap.parse_args()

    global docs, index
    os.makedirs(RAG_DIR, exist_ok=True)

    if args.reset:
        docs = []
        index = faiss.IndexFlatL2(EMBED_DIM)

    g = 0 if args.skip_guides else index_guides(args.guides_dir)
    s = index_scenes(args.scenes_dir)
    o = index_objects(args.objects_dir) if args.include_objects else 0

    _save()
    print(f"[rag_index_all] indexed: guides={g}, scenes={s}, objects={o}")
    print(f"[rag_index_all] docs.json -> {DOCS_FILE}")
    print(f"[rag_index_all] faiss     -> {INDEX_FILE}")

if __name__ == "__main__":
    main()

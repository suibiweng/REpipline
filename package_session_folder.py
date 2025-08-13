import json
import shutil
import sys
from pathlib import Path

# Config
OBJECTS_DIR = Path(r"H:\EditingReality\REpipline\objects")
PACKAGES_DIR = Path(r"H:\EditingReality\REpipline\packages")
ASSET_SUBDIRS = ["models", "meshes", "textures", "materials", "audio", "particles"]

def package_session_folder(session_json_path: Path):
    session_json_path = Path(session_json_path)
    with open(session_json_path, "r", encoding="utf-8") as f:
        session = json.load(f)

    session_id = session.get("sessionURLID")
    if not session_id:
        raise ValueError("sessionURLID missing from session JSON")

    # Create package folder like {session_id}_session_package
    package_root = PACKAGES_DIR / f"{session_id}_session_package"
    package_root.mkdir(parents=True, exist_ok=True)

    # Copy scene JSON
    shutil.copy2(session_json_path, package_root / session_json_path.name)

    # Loop over generateSpots IDs
    for spot in session.get("generateSpots", []):
        urlid = spot.get("id")
        if not urlid:
            continue

        src_object_dir = OBJECTS_DIR / urlid
        if not src_object_dir.exists():
            print(f"Warning: object folder not found: {src_object_dir}")
            continue

        dst_object_dir = package_root / urlid
        dst_object_dir.mkdir(exist_ok=True)

        # Copy code files
        for ext in (".json", ".lua", ".yaml", ".yml"):
            for file in src_object_dir.glob(f"*{ext}"):
                shutil.copy2(file, dst_object_dir / file.name)

        # Copy asset subfolders
        for sub in ASSET_SUBDIRS:
            src_sub = src_object_dir / sub
            if src_sub.exists():
                shutil.copytree(src_sub, dst_object_dir / sub, dirs_exist_ok=True)

    print(f"Packaged session into: {package_root}")
    return package_root

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python package_session_folder.py <path_to_session_json>")
        sys.exit(1)

    session_json_path = sys.argv[1]
    package_session_folder(session_json_path)

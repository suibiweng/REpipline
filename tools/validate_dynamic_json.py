import argparse, json, os, re, sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

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


def parse_iso8601(s: str) -> bool:
    if not isinstance(s, str) or not s:
        return False
    try:
        if s.endswith("Z"):
            datetime.fromisoformat(s[:-1] + "+00:00")
        else:
            datetime.fromisoformat(s)
        return True
    except Exception:
        return False


ACTIVATE_RE = re.compile(r'activateEffect\(\s*"([^"]+)"\s*\)')
TRIGGER_RE  = re.compile(r'\bfunction\s+trigger\s*\(')
LOCAL_RE    = re.compile(r'\blocal\s+')
ELLIPSIS_RE = re.compile(r'(\.\.\.|…)', re.UNICODE)


def extract_triggered_effects(lua_code: str) -> List[str]:
    if not isinstance(lua_code, str) or not lua_code:
        return []
    return list({m for m in ACTIVATE_RE.findall(lua_code)})


def validate(path: str, strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    errors: List[str] = []
    warns:  List[str] = []
    if not os.path.exists(path):
        return False, [f"File not found: {path}"], []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, [f"Invalid JSON: {e}"], []

    if not isinstance(data, dict):
        errors.append("Top-level must be a JSON object.")
        return False, errors, warns

    # object_name
    name = data.get("object_name")
    if not isinstance(name, str) or not name.strip():
        errors.append("Missing or empty 'object_name'.")
    elif is_id_shaped(name):
        warns.append("'object_name' looks ID-shaped (UUID/timestamp).")
        if strict:
            errors.append("ID-shaped 'object_name' not allowed in strict mode.")

    # created_at
    ts = data.get("created_at")
    if ts is not None and not parse_iso8601(ts):
        warns.append("'created_at' is not valid ISO-8601; will be ignored by some tools.")

    # particle_json
    pj = data.get("particle_json")
    if not isinstance(pj, list):
        errors.append("'particle_json' must be a list.")
    else:
        effect_names = set()
        for i, eff in enumerate(pj):
            if not isinstance(eff, dict):
                errors.append(f"particle_json[{i}] must be an object.")
                continue
            en = eff.get("effectName")
            if not isinstance(en, str) or not en.strip():
                errors.append(f"particle_json[{i}].effectName is required.")
            else:
                effect_names.add(en)
            # bursts repeatInterval >= 0
            emission = eff.get("emission")
            if isinstance(emission, dict):
                bursts = emission.get("bursts")
                if isinstance(bursts, list):
                    for j, b in enumerate(bursts):
                        if isinstance(b, dict):
                            ri = b.get("repeatInterval")
                            if ri is None:
                                continue
                            try:
                                if float(ri) < 0:
                                    errors.append(f"particle_json[{i}].emission.bursts[{j}].repeatInterval must be >= 0")
                            except Exception:
                                errors.append(f"particle_json[{i}].emission.bursts[{j}].repeatInterval must be a number")

    # lua_code quick checks
    lc = data.get("lua_code", "")
    if isinstance(lc, str) and lc.strip():
        if not TRIGGER_RE.search(lc):
            errors.append("lua_code must define function trigger().")
        if LOCAL_RE.search(lc):
            errors.append("lua_code must not use 'local' declarations (globals only per contract).")
        if ELLIPSIS_RE.search(lc):
            errors.append("lua_code contains ellipsis ('...' or '…'), which is forbidden in contract.")
        # effect references must exist
        missing = []
        effs = set()
        try:
            effs = set(extract_triggered_effects(lc))
        except Exception:
            pass
        if isinstance(pj, list):
            declared = {e.get("effectName") for e in pj if isinstance(e, dict) and e.get("effectName")}
            for nm in effs:
                if nm not in declared:
                    missing.append(nm)
        if missing:
            errors.append("Effects referenced in lua_code but missing from particle_json: " + ", ".join(sorted(missing)))

    ok = len(errors) == 0
    return ok, errors, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--strict", action="store_true", help="treat ID-shaped name and ts issues as errors")
    args = ap.parse_args()

    ok, errors, warns = validate(args.json_path, strict=args.strict)

    print(f"Validating: {args.json_path}")
    if warns:
        for w in warns:
            print("[warn]", w)
    if errors:
        for e in errors:
            print("[error]", e)
    print("Result:", "OK" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()

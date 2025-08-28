# NAME RESOLUTION GUIDE

This guide defines how `object_name` must be resolved.  
It enforces strict naming rules to avoid IDs, sessionURLIDs, or timestamp-like strings.  
**All final `object_name` values must be ALL CAPS WITH UNDERSCORES.**

---

## GENERAL PRINCIPLES

- `object_name` must always be a **human-readable ALL CAPS token**, never an ID.  
- Names must come from:  
  1. `SceneObjects[].name` (preferred if prompt indicates a real object).  
  2. `generate_spots[].gameObjectName` (preferred for generated objects).  
  3. Trimmed user prompt text, if no match above exists.  
- After derivation, always normalize to **ALL CAPS WITH UNDERSCORES**.  
- Absolutely forbidden:  
  - `id` values  
  - `sessionURLID`  
  - GUIDs  
  - UUID-like strings  
  - Pure timestamps or timestamp-like numbers  
  - Hex strings length ≥ 8  
- If resolution fails, set `object_name = ""` and explain in `comment`.

---

## DERIVATION ORDER

1. **If prompt begins with `[This is a real object in the space]`:**  
   - Find exact match in `SceneObjects[].name`.  
   - If found → set `object_name` to that name, converted to ALL CAPS WITH UNDERSCORES.  
   - If not found → set `object_name = ""` and include error in `comment`.  

2. **Else if prompt matches a generate_spots entry:**  
   - Use that entry’s `gameObjectName` as `object_name`, normalized to ALL CAPS WITH UNDERSCORES.  
   - If multiple close matches exist, choose the one whose `prompt` aligns best.  

3. **Else fallback to user prompt text:**  
   - Trim whitespace, strip quotes, collapse spaces.  
   - Normalize to ALL CAPS WITH UNDERSCORES.  

---

## PARTICLE-ONLY NAMING

- If output is **particle-only** (no Lua code):  
  - `object_name = "<EFFECTNAME>@EFFECT"`  
  - Example: if `effectName = "SmokeTrail"`, then `object_name = "SMOKE_TRAIL@EFFECT"`.  

---

## DUPLICATES

- If the chosen `object_name` already exists among generated objects:  
  - Append `(2)`, `(3)`, etc. while keeping it in ALL CAPS.  
  - Example: `"BASEBALL"` → `"BASEBALL (2)"`.  
- Never use IDs or timestamps for disambiguation.  

---

## FINAL ASSERTION

- Immediately before emitting JSON:  
  - Verify `object_name` is ALL CAPS and not ID-shaped.  
  - If invalid → re-run derivation.  
  - If still invalid → set `object_name = ""` and include explanation in `comment`.  

---

## LUA CONSISTENCY

- Since `object_name` is already ALL CAPS WITH UNDERSCORES in JSON, Lua comparisons can use it directly.  
- Example:  
  - `"object_name": "BASEBALL_BAT"`  
  - Lua: `if to_token(safe_get_name(other)) == "BASEBALL_BAT" then ... end`  

---

## EXAMPLES

### VALID
- Prompt: `"Baseball"`  
  - Output: `"object_name": "BASEBALL"`  
  - Lua comparisons: `"BASEBALL"`  

- Prompt: `"Wooden Chair"`  
  - Output: `"object_name": "WOODEN_CHAIR"`  
  - Lua comparisons: `"WOODEN_CHAIR"`  

- Particle-only:  
  - `"object_name": "SMOKE_TRAIL@EFFECT"`

### INVALID
- `"object_name": "67f92abcde1290"` (hex ID)  
- `"object_name": "20250827123045"` (timestamp)  
- `"object_name": "f47ac10b-58cc-4372-a567-0e02b2c3d479"` (UUID)  
- `"object_name": "sessionURLID"`  

---

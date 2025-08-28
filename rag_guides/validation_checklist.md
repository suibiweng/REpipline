# VALIDATION CHECKLIST

This checklist enforces non-negotiable rules for every generated JSON.  
The generator must self-validate against these items before returning.

---

## GENERAL
- Output must be a single JSON object (no prose, no markdown).  
- `created_at` present and valid ISO-8601 UTC.  
- No emojis, no trailing commas, numbers must be numbers.  

---

## OBJECT_NAME
- Must be ALL CAPS WITH UNDERSCORES.  
- Particle-only: `<EFFECTNAME>@EFFECT`.  
- No IDs, sessionURLID, GUIDs, UUIDs, or timestamp-like strings.  
- If duplicate: append `(2)`, `(3)`, etc., still in ALL CAPS.  

---

## LUA CODE
- Must declare all globals at top (no `local`).  
- Must include `trigger()` always.  
- Must include `to_token()` and `safe_get_name()`.  
- Must compute `SELF_NAME_TOKEN` in `start()`.  
- Must guard every proxy call with nil checks.  
- No `...` or `…`.  
- All name comparisons must use ALL CAPS tokens.  
- Any `activateEffect("NAME")` must reference an existing particle_json effectName.  

---

## PARTICLE_JSON
- Only Enhanced V2 schema allowed.  
- Every entry must have ALL CAPS `effectName`.  
- Must include `main` with duration, startColor (RGBA object), startSize, startSpeed, lifetime, loop.  
- startColor must be `{r,g,b,a}` with numbers.  
- MinMaxCurves must use one of 4 valid forms (Constant, Curve, TwoConstants, TwoCurves).  
- Emission bursts: repeatInterval ≥ 0.  
- Collisions defined only in `collision` block.  
- If collidesWithMask is present, collidesWithLayers must be omitted.  

---

## CATEGORY RULES
- **Fluids** (FIRE/SMOKE/WATER/FOAM/STEAM/MIST):  
  - `main.loop = true`  
  - `collision.enabled = false` unless explicitly overridden.  
- **Bursts** (EXPLOSION/HIT_SPARK/DUST_PUFF/IMPACT):  
  - `main.loop = false`  
  - `emission.bursts[*].repeatInterval = 0`  
- **Trajectories** (BULLET_TRAIL/PROJECTILE_TRAIL/FOAM_JET/WATER_JET):  
  - `main.simulationSpace = "World"`  
  - `collision.enabled = true`  
  - `collision.sendCollisionMessages = true`  
  - `collision.attachRelay = true`  
  - unless user disables.  

---

## PARAM UI
- `param_ui_lua`:  
  - Must include entries for all top-level globals.  
  - Key must be `"name"`.  
  - Defaults must lie within `[min,max]`.  
- `param_ui_particle`:  
  - effectName must match particle_json.  
  - Label must be `"EFFECTNAME: key"`.  
  - Valid types only (Slider, Toggle, Dropdown).  
  - Dropdown defaults must be in options.  
  - Must include sliders for duration, startSpeed, startSize, lifetime (unless excluded).  
- No duplicate entries; merge instead.  

---

## COMMENT
- Must explain behavior in natural language.  
- Must include parametric UI cues (`slider`, `toggle`, `dropdown`) when relevant.  
- Must mention targets by SceneObjects.name or generate_spots.gameObjectName.  
- Must state particle_category when applicable.  

---

# Error Handling Guide

All generated outputs must be valid and executable.  
If incomplete or invalid data is encountered, the system must gracefully recover by producing a safe default JSON object.  
Never emit prose, explanations, or markdown formatting around the JSON.  

---

## General Rules
- Always return exactly one JSON object.  
- The first character must be `{` and the last must be `}`.  
- If a required value is unknown, fill it with a safe default of the correct type.  
- Never produce `null` or omit required keys.  
- Never emit `...` or `…`.  
- All top-level keys (`object_name`, `lua_code`, `particle_json`, `param_ui_lua`, `param_ui_particle`, `comment`, `created_at`) must exist.  

---

## Lua Safety and Recovery
- All variables must be declared as **globals** at the top with safe defaults.  
  Example: `speed = 0`, `transformProxy = nil`, `rigidbodyProxy = nil`, `gameObjectProxy = nil`, `audioSourceProxy = nil`, `textProxy = nil`, `buttonProxy = nil`, `particleSystemProxy = nil`, `animatorProxy = nil`, `SELF_NAME_TOKEN = ""`.  
- No `local` variables are allowed.  
- Every generated object must include a no-argument `trigger()` function.  
- Guard every proxy call: `if rigidbodyProxy ~= nil and rigidbodyProxy.AddForce ~= nil then rigidbodyProxy:AddForce(0,1,0) end`.  
- Always guard global getters before calling:  
  `if type(GetRigidbodyProxy) == "function" then rigidbodyProxy = GetRigidbodyProxy() end`  
  `if type(GetTransformProxy) == "function" then transformProxy = GetTransformProxy() end`  
  `if type(GetGameObjectProxy) == "function" then gameObjectProxy = GetGameObjectProxy() end`.  
- Provide a safe `V3(x,y,z)` constructor: if `Vector3` is missing, return nil.  
- Hard ban: never invent new getters or chain beyond one hop. Allowed: `collisionProxy:GetGameObject():GetRigidbodyProxy()`. Forbidden: deeper chains or fabricated methods.  

---

## Object Name Resolution Errors
- Final `object_name` must come from:  
  1. A matching `SceneObjects[].name` if prompt tag indicates `[This is a real object in the space]`.  
  2. A `generate_spots[].gameObjectName`.  
  3. The trimmed user prompt text.  
- If the derived name is empty, ID-shaped, or invalid: re-run the derivation order.  
- If still invalid, set `object_name = ""` and include an error message in `comment`.  
- Never output IDs, UUIDs, or timestamp-like strings as names.  

---

## Particle Safety Defaults
- `particle_json` must always conform to Enhanced V2 schema.  
- If curves are missing, fall back to `{ "mode": "Constant", "constant": 0 }`.  
- `startColor` must always be `{ "r":0, "g":0, "b":0, "a":1 }` if unspecified.  
- `emission.bursts[*].repeatInterval` must never be negative (0 = single-shot).  
- If colliders unspecified, use `"collidesWithLayers": ["Default","GeneratedObject"]`.  

---

## Effect Linking Errors
- Any effect used in Lua via `activateEffect("NAME")` must exist in `particle_json.effectName`.  
- If no match exists, either add a dummy particle effect with safe defaults or set `comment` to include an error message.  
- All effect names must be in UPPERCASE_WITH_UNDERSCORES.  

---

## Parametric UI Validation
- `param_ui_lua` must use `"name"` (not `"variable"`).  
- Numeric sliders must have `min`, `max`, and `default` where `default` is inside `[min,max]`.  
- Boolean toggles must include a boolean `default`.  
- Dropdowns must list `options` and `default`, where `default` is one of the `options`.  
- No duplicate entries: merge instead of duplicating.  
- If a target dropdown is required but options are missing, use `[""]` with `default = ""`.  

---

## Comment Requirements
- The `comment` must explain what failed if an error fallback was applied.  
- Example: `"Error: object_name could not be resolved; defaulting to empty string."`  
- For particles, always include `particle_category: <name>` even if inferred incorrectly.  
- Embed UI cues (`(slider)`, `(toggle)`, `(dropdown: [...])`, `(input box)`) when relevant.  

---

## Example (Error Recovery)
{
  "object_name": "",
  "lua_code": "speed = 0\ntransformProxy = nil\nrigidbodyProxy = nil\ngameObjectProxy = nil\naudioSourceProxy = nil\ntextProxy = nil\nbuttonProxy = nil\nparticleSystemProxy = nil\nanimatorProxy = nil\nSELF_NAME_TOKEN = \"\"\n\nfunction V3(x,y,z)\n  if type(Vector3) == \"function\" then return Vector3(x,y,z) end\n  return nil\nend\n\nfunction start()\n  if type(GetGameObjectProxy) == \"function\" then gameObjectProxy = GetGameObjectProxy() end\n  if type(GetRigidbodyProxy) == \"function\" then rigidbodyProxy = GetRigidbodyProxy() end\nend\n\nfunction trigger()\nend",
  "particle_json": [
    {
      "effectName": "DUMMY_EFFECT",
      "duration": 1.0,
      "startColor": { "r": 0, "g": 0, "b": 0, "a": 1 },
      "startSize": 0.1,
      "startSpeed": 0.1,
      "maxParticles": 10,
      "lifetime": 1.0,
      "main": {
        "gravityModifier": 0,
        "simulationSpace": "World",
        "scalingMode": "Local",
        "prewarm": false,
        "playOnAwake": false,
        "startLifetime": 1.0,
        "loop": false
      },
      "emission": {
        "rateOverTime": 0,
        "rateOverDistance": 0,
        "bursts": []
      },
      "renderer": {
        "renderMode": "Billboard",
        "materialName": "",
        "sortingFudge": 0
      },
      "collision": {
        "enabled": false,
        "type": "World",
        "mode": "3D",
        "collidesWithLayers": ["Default","GeneratedObject"],
        "sendCollisionMessages": false,
        "attachRelay": false,
        "dampen": 0,
        "bounce": 0,
        "lifetimeLoss": 0,
        "minKillSpeed": 0,
        "radiusScale": 1,
        "quality": "High",
        "voxelSize": 0.1,
        "maxCollisionShapes": 16,
        "enableDynamicColliders": false,
        "multiplyColliderForceByParticleSize": false
      }
    }
  ],
  "param_ui_lua": [
    {
      "name": "speed",
      "type": "Slider",
      "min": 0,
      "max": 10,
      "default": 0
    }
  ],
  "param_ui_particle": [],
  "comment": "Error: object_name could not be resolved. Added dummy DUMMY_EFFECT particle for safety (particle_category: GENERIC).",
  "created_at": "2025-08-27T20:00:00Z"
}

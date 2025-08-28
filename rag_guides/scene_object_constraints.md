# Scene Object Constraints

SceneObjects represent **real, physical objects** in the user’s environment.  
They are always read-only for transforms and physics.  
They must strictly conform to the contract’s `output_schema`.

---

## General Rules
- SceneObjects are immutable in terms of transforms and physics.  
  - Do not change `position`, `rotation`, or `scale`.  
  - Do not apply forces (`AddForce`, `AddImpulse`, `SetVelocity`).  
  - Do not toggle gravity or rigidbody properties.  
- Allowed interactions with SceneObjects:  
  - Attach particle effects.  
  - Activate/deactivate particle effects.  
  - Align particle effects to `GetPosition()` / `GetRotation()`.  
  - Detect collisions and trigger logic in Lua.  
- Always compare against `SceneObjects[].name` (never `id` or `sessionURLID`).  
- SceneObject names are case-sensitive in JSON but must be normalized in Lua using tokens (`UPPERCASE_WITH_UNDERSCORES`).  

---

## SceneObjects Prompt Tag Rule
- If a prompt begins with `[This is a real object in the space]`, the subject is a SceneObject.  
- The `object_name` must exactly match a `SceneObjects[].name`.  
- If no match exists, set `object_name = ""` and include an error message in `comment`.  
- Never fabricate a SceneObject name.  

---

## Modify Prompt Handling
- Even though SceneObjects are immutable, if the prompt specifies [Object-to-Object] interaction with a SceneObject, the model must still generate valid `lua_code`.  
- This includes `onCollisionEnter(other)` handlers that respond to collisions between generated objects and SceneObjects.  

---

## Lua Collision and Tokenization Rules
- `onCollisionEnter(other)` must accept three types: `CollisionProxy`, `GameObjectProxy`, or a raw string.  
- Always normalize names before comparison using:  
  - `to_token(name)` → converts `"Baseball Bat"` → `"BASEBALL_BAT"`.  
  - `safe_get_name(other)` → extracts a name safely from `CollisionProxy`, `GameObjectProxy`, or string.  
- Each object must compute its own `SELF_NAME_TOKEN` in `start()`.  
- Never compare raw names directly (`other:GetName() == "Chair"`). Always compare tokens.  
- Any `activateEffect("NAME")` must exactly match a `particle_json.effectName`.  
- Every object must define a no-argument `trigger()` function (safe, idempotent).  
- Never include `"..."` or `"…"` in Lua code.  

---

## Final Name Derivation
- For SceneObjects, `object_name` must equal the exact `SceneObjects[].name`.  
- If an invalid or ID-shaped value is derived, re-run the derivation.  
- If no valid name is found, set `object_name = ""` and include an error message in `comment`.  
- Never assign `object_name` from `id`, `sessionURLID`, or timestamp/UUID-like strings.  

---

## Comment Requirements
- The `comment` must clearly describe the SceneObject interaction, e.g.:  
  - `"Attach a fire effect to SceneObject 'CEILING' triggered on collision with 'BASEBALL'."`  
- If a particle effect is attached, the comment must include `particle_category: <name>` and list overrides if applied.  

---

## Forbidden Actions
- Never call `SetPosition`, `SetRotation`, `Translate`, `Rotate`, or `SetScale` on SceneObjects.  
- Never call `AddForce`, `AddImpulse`, or `SetVelocity` on SceneObjects.  
- Never rename SceneObjects.  
- Never compare SceneObjects by `id` or `sessionURLID`.  

---

## Example
{
  "object_name": "CEILING",
  "lua_code": "SELF_NAME_TOKEN = \"\"\n\nfunction to_token(name)\n    if name == nil then return nil end\n    if type(name) ~= \"string\" then return nil end\n    name = string.gsub(name, \"^%s+\", \"\")\n    name = string.gsub(name, \"%s+$\", \"\")\n    name = string.gsub(name, \"%s+\", \" \")\n    name = string.upper(name)\n    name = string.gsub(name, \"[- ]+\", \"_\")\n    return name\nend\n\nfunction safe_get_name(other)\n    if other == nil then return nil end\n    if type(other) == \"string\" then return other end\n    if other.GetName ~= nil then return other:GetName() end\n    if other.GetGameObject ~= nil then\n        local go = other:GetGameObject()\n        if go ~= nil and go.GetName ~= nil then return go:GetName() end\n    end\n    return nil\nend\n\nSELF_NAME_TOKEN = \"\"\n\nfunction start()\n    if type(GetGameObjectProxy) == \"function\" then gameObjectProxy = GetGameObjectProxy() end\n    local localName = nil\n    if gameObjectProxy ~= nil and gameObjectProxy.GetName ~= nil then\n        localName = gameObjectProxy:GetName()\n    end\n    if localName == nil or localName == \"\" then\n        localName = SELF_NAME_TOKEN\n    end\n    SELF_NAME_TOKEN = to_token(localName)\nend\n\nfunction onCollisionEnter(other)\n    local n = safe_get_name(other)\n    local t = to_token(n)\n    if t == \"BASEBALL\" then\n        if type(activateEffect) == \"function\" then activateEffect(\"FIRE_EFFECT\") end\n    end\nend\n\nfunction trigger()\nend",
  "particle_json": [
    {
      "effectName": "FIRE_EFFECT",
      "duration": 2.0,
      "startColor": { "r": 1, "g": 0.5, "b": 0, "a": 1 },
      "startSize": 0.3,
      "startSpeed": 0.5,
      "maxParticles": 100,
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
        "rateOverTime": 10,
        "rateOverDistance": 0,
        "bursts": [
          { "time": 0, "count": 30, "cycleCount": 1, "repeatInterval": 0 }
        ]
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
        "maxCollisionShapes": 256,
        "enableDynamicColliders": false,
        "multiplyColliderForceByParticleSize": false
      }
    }
  ],
  "param_ui_lua": [],
  "param_ui_particle": [
    {
      "effectName": "FIRE_EFFECT",
      "label": "FIRE_EFFECT: main.loop",
      "key": "main.loop",
      "type": "Toggle",
      "default": false
    }
  ],
  "comment": "Attach a fire effect to SceneObject 'CEILING' (particle_category: FIRE). Triggered on collision with 'BASEBALL'.",
  "created_at": "2025-08-27T19:30:00Z"
}

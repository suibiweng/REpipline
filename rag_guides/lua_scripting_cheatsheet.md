# Lua Scripting Cheatsheet

This cheatsheet defines the allowed proxies, helper functions, and Lua rules.  
All generated `lua_code` must strictly follow these conventions.

---

## Global Rules
- All variables must be declared as **globals** at the top with safe defaults. Example: `speed = 0`, `transformProxy = nil`, `rigidbodyProxy = nil`, `gameObjectProxy = nil`, `audioSourceProxy = nil`, `textProxy = nil`, `buttonProxy = nil`, `particleSystemProxy = nil`, `animatorProxy = nil`, `SELF_NAME_TOKEN = ""`.  
- Never use `local`.  
- Never use `...` or `…`.  
- Always define `trigger()` (safe, idempotent).  
- Guard all proxy calls with nil checks.  
- Always guard getters: `if type(GetRigidbodyProxy) == "function" then rigidbodyProxy = GetRigidbodyProxy() end`.  
- Use safe constructors: `function V3(x,y,z) if type(Vector3)=="function" then return Vector3(x,y,z) end return nil end`. Same pattern applies for `Vector2`, `Color`, `Quaternion`.  

---

## Allowed Proxies
- **transformProxy**: `GetPosition()`, `SetPosition()`, `Translate()`, `Rotate()`, `SetRotation()`, `GetRotation()`, `GetScale()`, `SetScale()`.  
- **gameObjectProxy**: `GetName()`, `SetName()`, `IsActive()`, `SetActive()`, `GetTag()`, `GetTransformProxy()`, `GetRigidbodyProxy()`, `GetAudioSourceProxy()`, `GetAnimatorProxy()`.  
- **rigidbodyProxy**: `AddForce(x,y,z)`, `AddForce(Vector3,"Mode")`, `AddForce(x,y,z,"Mode")`, `AddImpulse(x,y,z)`, `SetVelocity(x,y,z)`, `SetVelocity(Vector3)`, `GetVelocity()`, `SetUseGravity(bool)`.  
- **audioSourceProxy**: `Play()`, `Stop()`, `Pause()`, `SetVolume()`, `SetLoop()`.  
- **textProxy**: `SetText()`, `GetText()`, `SetColor()`.  
- **buttonProxy**: `SetInteractable()`, `IsInteractable()`.  
- **particleSystemProxy**: `Play()`, `Stop()`, `SetLooping()`, `IsPlaying()`.  
- **animatorProxy**: `Play(stateName)`, `SetBool(name,bool)`, `SetTrigger(name)`.  
- **collisionProxy**: `GetGameObject()`, `GetRigidbodyProxy()`, `GetContactPoint()`, `GetRelativeVelocity()`, `GetName()`.  

---

## Proxy Usage Rules
- Never call `GetGameObject()` on GameObjectProxy. Only CollisionProxy implements `GetGameObject()`.  
- Allowed one-hop chains: `collisionProxy:GetGameObject():GetRigidbodyProxy()`.  
- Forbidden: deeper chains or invented getters.  
- Always nil-check before calling methods.  

---

## Collision Handling Helpers
- Always include `to_token(name)` to normalize strings into `UPPERCASE_WITH_UNDERSCORES`.  
- Always include `safe_get_name(other)` to extract names safely.  
- Each object must compute `SELF_NAME_TOKEN` in `start()`.  

Example pattern:  
function to_token(name)
  if name == nil then return nil end
  if type(name) ~= "string" then return nil end
  name = string.gsub(name, "^%s+", "")
  name = string.gsub(name, "%s+$", "")
  name = string.gsub(name, "%s+", " ")
  name = string.upper(name)
  name = string.gsub(name, "[- ]+", "_")
  return name
end

function safe_get_name(other)
  if other == nil then return nil end
  if type(other) == "string" then return other end
  if other.GetName ~= nil then return other:GetName() end
  if other.GetGameObject ~= nil then
    local go = other:GetGameObject()
    if go ~= nil and go.GetName ~= nil then return go:GetName() end
  end
  return nil
end

SELF_NAME_TOKEN = ""

function start()
  if type(GetGameObjectProxy) == "function" then gameObjectProxy = GetGameObjectProxy() end
  local localName = nil
  if gameObjectProxy ~= nil and gameObjectProxy.GetName ~= nil then
    localName = gameObjectProxy:GetName()
  end
  if localName == nil or localName == "" then
    localName = SELF_NAME_TOKEN
  end
  SELF_NAME_TOKEN = to_token(localName)
end

---

## Trigger Function
Every object must define a `trigger()` function: it must exist even if empty, be safe to call multiple times, and guard all calls inside. Example:  
function trigger()
  if rigidbodyProxy ~= nil and rigidbodyProxy.AddImpulse ~= nil then
    rigidbodyProxy:AddImpulse(0, 2, 0)
  end
  if type(activateEffect) == "function" then
    activateEffect("HIT_SPARK")
  end
end

---

## Forbidden Actions
- Do not use IDs, sessionURLID, or timestamp-like strings for names.  
- Do not rename SceneObjects.  
- Do not move or apply forces to SceneObjects.  
- Do not use `local`.  
- Do not use `...` or `…`.  
- Do not invent getters or chain beyond one hop.  

---

## Example Snippet
{
  "object_name": "BASEBALL",
  "lua_code": "speed = 10\nSELF_NAME_TOKEN = \"\"\n\nfunction to_token(name)\n  if name == nil then return nil end\n  if type(name) ~= \"string\" then return nil end\n  name = string.gsub(name, \"^%s+\", \"\")\n  name = string.gsub(name, \"%s+$\", \"\")\n  name = string.gsub(name, \"%s+\", \" \")\n  name = string.upper(name)\n  name = string.gsub(name, \"[- ]+\", \"_\")\n  return name\nend\n\nfunction safe_get_name(other)\n  if other == nil then return nil end\n  if type(other) == \"string\" then return other end\n  if other.GetName ~= nil then return other:GetName() end\n  if other.GetGameObject ~= nil then\n    local go = other:GetGameObject()\n    if go ~= nil and go.GetName ~= nil then return go:GetName() end\n  end\n  return nil\nend\n\nfunction V3(x,y,z)\n  if type(Vector3) == \"function\" then return Vector3(x,y,z) end\n  return nil\nend\n\nfunction start()\n  if type(GetGameObjectProxy) == \"function\" then gameObjectProxy = GetGameObjectProxy() end\n  if type(GetRigidbodyProxy) == \"function\" then rigidbodyProxy = GetRigidbodyProxy() end\n  local localName = nil\n  if gameObjectProxy ~= nil and gameObjectProxy.GetName ~= nil then\n    localName = gameObjectProxy:GetName()\n  end\n  if localName == nil or localName == \"\" then localName = SELF_NAME_TOKEN end\n  SELF_NAME_TOKEN = to_token(localName)\nend\n\nfunction update(deltaTime)\n  if rigidbodyProxy ~= nil and rigidbodyProxy.AddForce ~= nil then\n    rigidbodyProxy:AddForce(0, 0, -1 * speed)\n  end\nend\n\nfunction onCollisionEnter(other)\n  local n = safe_get_name(other)\n  local t = to_token(n)\n  if t == \"WALL_FACE\" then\n    if type(activateEffect) == \"function\" then activateEffect(\"HIT_SPARK\") end\n  end\nend\n\nfunction trigger()\n  if rigidbodyProxy ~= nil and rigidbodyProxy.AddImpulse ~= nil then\n    rigidbodyProxy:AddImpulse(0, 2, 0)\n  end\nend",
  "particle_json": [
    {
      "effectName": "HIT_SPARK",
      "duration": 0.5,
      "startColor": { "r": 1, "g": 1, "b": 0, "a": 1 },
      "startSize": 0.2,
      "startSpeed": 0.5,
      "maxParticles": 50,
      "lifetime": 0.5,
      "main": {
        "gravityModifier": 0,
        "simulationSpace": "World",
        "scalingMode": "Local",
        "prewarm": false,
        "playOnAwake": false,
        "startLifetime": 0.5,
        "loop": false
      },
      "emission": {
        "rateOverTime": 0,
        "rateOverDistance": 0,
        "bursts": [
          { "time": 0, "count": 15, "cycleCount": 1, "repeatInterval": 0 }
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
        "maxCollisionShapes": 64,
        "enableDynamicColliders": false,
        "multiplyColliderForceByParticleSize": false
      }
    }
  ],
  "param_ui_lua": [
    { "name": "speed", "type": "Slider", "min": 0, "max": 20, "default": 10 }
  ],
  "param_ui_particle": [
    { "effectName": "HIT_SPARK", "label": "HIT_SPARK: main.loop", "key": "main.loop", "type": "Toggle", "default": false }
  ],
  "comment": "A baseball moves forward with adjustable speed (slider). On collision with WALL_FACE (dropdown), triggers HIT_SPARK (particle_category: BURST).",
  "created_at": "2025-08-27T20:30:00Z"
}

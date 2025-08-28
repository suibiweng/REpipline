# Collision Handling Guide

This guide defines how collisions must be handled in Lua code.  
All generated `lua_code` must strictly follow these rules.

---

## General Rules
- All objects must define `onCollisionEnter(other)` even if it only checks and returns.  
- The `other` argument may be:  
  - A `CollisionProxy`  
  - A `GameObjectProxy`  
  - A raw string name  
- Always normalize names before comparison using `to_token()` and `safe_get_name()`.  
- All objects must compute `SELF_NAME_TOKEN` in `start()` and use it for self-comparison.  
- Never compare raw names (e.g., `other:GetName() == "Chair"`). Always use tokenized names.  
- Always guard proxy calls with nil checks.  

---

## Required Helpers

Every generated `lua_code` **must include these helper functions** at the top:

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

## Collision Usage Rules
- Always extract `t = to_token(safe_get_name(other))` before comparing.  
- Only compare against known SceneObjects[].name or generate_spots[].gameObjectName (never IDs).  
- Allowed actions on collision:  
  - Activate/deactivate particle effects.  
  - Apply forces to other virtual objects (never to SceneObjects).  
  - Trigger object’s own state change.  
- All Lua comparisons must be in `UPPERCASE_WITH_UNDERSCORES`.  

---

## Example Collision Logic
function onCollisionEnter(other)
  local n = safe_get_name(other)
  local t = to_token(n)
  if t == "BASEBALL" then
    if type(activateEffect) == "function" then activateEffect("HIT_SPARK") end
  elseif t == "WALL_FACE" then
    if rigidbodyProxy ~= nil and rigidbodyProxy.AddImpulse ~= nil then
      rigidbodyProxy:AddImpulse(0, 2, 0)
    end
  end
end

---

## Example JSON
{
  "object_name": "WALL_FACE",
  "lua_code": "SELF_NAME_TOKEN = \"\"\n\nfunction to_token(name)\n  if name == nil then return nil end\n  if type(name) ~= \"string\" then return nil end\n  name = string.gsub(name, \"^%s+\", \"\")\n  name = string.gsub(name, \"%s+$\", \"\")\n  name = string.gsub(name, \"%s+\", \" \")\n  name = string.upper(name)\n  name = string.gsub(name, \"[- ]+\", \"_\")\n  return name\nend\n\nfunction safe_get_name(other)\n  if other == nil then return nil end\n  if type(other) == \"string\" then return other end\n  if other.GetName ~= nil then return other:GetName() end\n  if other.GetGameObject ~= nil then\n    local go = other:GetGameObject()\n    if go ~= nil and go.GetName ~= nil then return go:GetName() end\n  end\n  return nil\nend\n\nfunction V3(x,y,z)\n  if type(Vector3) == \"function\" then return Vector3(x,y,z) end\n  return nil\nend\n\nfunction start()\n  if type(GetGameObjectProxy) == \"function\" then gameObjectProxy = GetGameObjectProxy() end\n  if type(GetRigidbodyProxy) == \"function\" then rigidbodyProxy = GetRigidbodyProxy() end\n  local localName = nil\n  if gameObjectProxy ~= nil and gameObjectProxy.GetName ~= nil then\n    localName = gameObjectProxy:GetName()\n  end\n  if localName == nil or localName == \"\" then localName = SELF_NAME_TOKEN end\n  SELF_NAME_TOKEN = to_token(localName)\nend\n\nfunction onCollisionEnter(other)\n  local n = safe_get_name(other)\n  local t = to_token(n)\n  if t == \"BASEBALL\" then\n    if type(activateEffect) == \"function\" then activateEffect(\"HIT_SPARK\") end\n  elseif t == \"WALL_FACE\" then\n    if rigidbodyProxy ~= nil and rigidbodyProxy.AddImpulse ~= nil then\n      rigidbodyProxy:AddImpulse(0, 2, 0)\n    end\n  end\nend\n\nfunction trigger()\nend",
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
          { "time": 0, "count": 10, "cycleCount": 1, "repeatInterval": 0 }
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
        "collidesWithLayers": ["Default", "GeneratedObject"],
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
  "param_ui_lua": [],
  "param_ui_particle": [
    {
      "effectName": "HIT_SPARK",
      "label": "HIT_SPARK: main.loop",
      "key": "main.loop",
      "type": "Toggle",
      "default": false
    }
  ],
  "comment": "WALL_FACE triggers HIT_SPARK (particle_category: BURST) on collision with BASEBALL.",
  "created_at": "2025-08-27T21:00:00Z"
}

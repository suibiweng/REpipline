# Parametric UI Rules

Parametric UI definitions expose tunable values from Lua globals and particle properties.  
They must strictly conform to the contract’s `output_schema`.

---

## General Generation Rules
- Always generate **`param_ui_lua`** entries for all top-level Lua variables declared before `start()` if they are numeric, boolean, or string.
  - ❌ Do NOT include Unity engine proxies (gameObjectProxy, rigidbodyProxy, transformProxy, audioSourceProxy, textProxy, buttonProxy, particleSystemProxy, animatorProxy).

  - Numeric → Slider  
    - Must include `min`, `max`, `default`.  
    - All values must be numbers, not strings.  
    - `default` must lie inside `[min,max]`.  
    - Default = value from code if present, else midpoint.  
  - Boolean → Toggle  
    - Must include a boolean `default`.  
    - Default = value from code if present, else `false`.  
  - String → InputField  
    - Must include a string `default`.  
    - Default = value from code if present, else `""`.  
  

- Every `param_ui_lua` item MUST use the field `name` (never `variable` or `key`).  

- If the `comment` includes UI cues, they must be mapped exactly:  
  - `(slider)` → Slider with min, max, default.  
  - `(toggle)` → Toggle with default.  
  - `(dropdown: [...])` → Dropdown with options and default.  
  - `(input box)` → InputField with default "".  

- Always include a `target` Dropdown if Lua code or comment references object names (for collisions/interactions).  
  - Populate `options` from all known `SceneObjects[].name` and `generate_spots[].gameObjectName`.  
  - The `default` must be one of the listed options.  

- No duplicate entries. If a key is repeated, merge ranges/defaults instead of creating duplicates.  

---

## Particle-Specific Rules
- Every `param_ui_particle` entry must include:  
  - `effectName`  
  - `label` (format: `"EffectName: key"`)  
  - `key`  
  - `type`  

- `effectName` MUST exactly match one defined in `particle_json.effectName`.  

- Type rules:  
  - Slider → numeric property (`min`, `max`, `default` required).  
    - All numeric values must be numbers (not strings).  
    - `default` must lie inside `[min,max]`.  
  - Toggle → boolean property (`default` required).  
  - Dropdown → string property (`options` + `default` required).  
    - `default` must always be one of the listed `options`.  

- Valid keys (UI-safe particle fields):  
  - Booleans (Toggle): `main.loop`, `main.prewarm`, `main.playOnAwake`, `noise.enabled`, `trails.enabled`, `trails.dieWithParticles`.  
  - Numbers (Slider): `duration`, `startSpeed`, `startSize`, `lifetime`, `emission.rateOverTime`, `emission.rateOverDistance`, `emission.bursts[0].count`, `noise.strength`, `noise.frequency`, `noise.scrollSpeed`, `noise.octaveCount`, `trails.lifetime`, `trails.ratio`, `renderer.sortingFudge`, `sizeOverLifetime.size.constant`, `rotationOverLifetime.z.constant`, `velocityOverLifetime.x.constant`, `velocityOverLifetime.y.constant`, `velocityOverLifetime.z.constant`, `velocityOverLifetime.speedModifier.constant`.  
  - Strings (Dropdown): `renderer.renderMode` (options = `[Billboard, StretchedBillboard, HorizontalBillboard, VerticalBillboard, Mesh]`).  

- Always include sliders for:  
  - `duration`  
  - `startSpeed`  
  - `startSize`  
  - `lifetime`  
  (unless the prompt explicitly excludes them).  

- If only one particle effect exists, reuse that `effectName` for all particle UI controls.  

- Labels must always be formatted as `"EffectName: key"`.  

---

## Category-Based UI Rules
- Fluids (FIRE/SMOKE/WATER/FOAM/STEAM/MIST):  
  - Add `main.loop` Toggle, default = true.  
  - Do not include `collision.enabled` UI control.  

- Bursts (EXPLOSION/HIT_SPARK/DUST_PUFF/IMPACT):  
  - Add `main.loop` Toggle, default = false.  
  - Do not include `collision.enabled` UI control.  

- Trajectories (BULLET_TRAIL/PROJECTILE_TRAIL/FOAM_JET/WATER_JET):  
  - Add `main.loop` Toggle, default = false.  
  - Add `collision.enabled` Toggle, default = true.  

- Category overrides:  
  - If the user explicitly mentions `looping` or `one-shot`, respect that over defaults.  
  - If the user explicitly mentions `no collision`, set `collision.enabled = false` even for trajectory categories.  
  - If ambiguous, fall back to safe defaults (fluids: loop=true, no collision; bursts: loop=false).  

---

## Comment Integration Rules
- The `comment` field must always carry UI cues for runtime parsing, e.g.:  
  - `"speed (slider)"`  
  - `"target (dropdown: [WALL_FACE, CHAIR])"`  
  - `"loop (toggle)"`  
  - `"label (input box)"`.  
- For particle effects, the `comment` must also include `particle_category: <name>` and list any overrides (e.g., `"particle_category: FIRE, loop=false override"`).  
- `comment` is mandatory. It must:
  - Describe the object’s behavior in natural language.
  - Embed explicit UI cues (e.g., speed (slider), bounce (toggle), effect (dropdown: [Explosion, Smoke])).
  - Match the actual `param_ui_lua` and `param_ui_particle` entries.


---

## Example
{
  "object_name": "BALL",
  "lua_code": "speed = 10\n\nfunction start()\n    if type(GetRigidbodyProxy) == \"function\" then rigidbodyProxy = GetRigidbodyProxy() end\nend\n\nfunction update(deltaTime)\n    if rigidbodyProxy ~= nil and rigidbodyProxy.AddForce ~= nil then\n        rigidbodyProxy:AddForce(0, speed, 0)\n    end\nend\n\nfunction trigger()\nend",
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
        "loop": true
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
  "param_ui_lua": [
    {
      "name": "speed",
      "type": "Slider",
      "min": 0,
      "max": 20,
      "default": 10
    },
    {
      "name": "target",
      "type": "Dropdown",
      "options": ["WALL_FACE","CHAIR"],
      "default": "WALL_FACE"
    }
  ],
  "param_ui_particle": [
    {
      "effectName": "FIRE_EFFECT",
      "label": "FIRE_EFFECT: duration",
      "key": "duration",
      "type": "Slider",
      "min": 0,
      "max": 10,
      "default": 2
    },
    {
      "effectName": "FIRE_EFFECT",
      "label": "FIRE_EFFECT: main.loop",
      "key": "main.loop",
      "type": "Toggle",
      "default": true
    }
  ],
  "comment": "Ball with adjustable speed (slider). Plays FIRE_EFFECT (particle_category: FIRE) on loop. Target (dropdown: [WALL_FACE, CHAIR]).",
  "created_at": "2025-08-27T18:30:00Z"
}

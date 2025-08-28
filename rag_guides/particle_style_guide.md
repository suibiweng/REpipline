# Particle Style Guide

Particle effects must always conform to the Enhanced V2 schema.  
Legacy/simple fields are strictly forbidden.  
All outputs must follow the contract’s `output_schema`.

---

## General Rules
- Use only the Enhanced V2 module-based schema.  
- Required top-level fields per effect: `effectName`, `duration`, `startColor`, `startSize`, `startSpeed`, `maxParticles`, `lifetime`, plus module objects (`main`, `shapeModule`, `emission`, `velocityOverLifetime`, `colorOverLifetime`, `sizeOverLifetime`, `rotationOverLifetime`, `noise`, `trails`, `renderer`, `collision`).  
- `startColor` must be an object `{r:number,g:number,b:number,a:number}`.  
- MinMaxCurve must take one of the valid forms:  
  - `{"mode":"Constant","constant":N}`  
  - `{"mode":"Curve","curve":[{"time":0.0,"value":N},...]}`  
  - `{"mode":"TwoConstants","constantMin":N,"constantMax":N}`  
  - `{"mode":"TwoCurves","curveMin":[...],"curveMax":[...]}`.  
- `emission.bursts[*].repeatInterval` must be ≥ 0 (0 = single-shot).  
- Collisions must be defined only under the `collision` object.  
- Prefer `collidesWithLayers: ["Default","GeneratedObject"]` for clarity. If `collidesWithMask` is used, omit `collidesWithLayers` entirely.  

---

## Category Defaults
### Fluids (FIRE / SMOKE / WATER / FOAM / STEAM / MIST)
- `main.loop = true` (default).  
- `collision.enabled = false`.  
- Noise defaults:  
  - `noise.enabled = true`  
  - `noise.strength = 0.3`  
  - `noise.frequency = 0.2`  
  - `noise.scrollSpeed = 0.15`  
  - `noise.octaveCount = 2`  
  - `noise.quality = "Medium"`  
- Velocity over Lifetime: upward drift.  
  - `velocityOverLifetime.enabled = true`  
  - `velocityOverLifetime.space = "World"`  
  - `velocityOverLifetime.y = {"mode":"Constant","constant":0.6}`  
- Renderer: `Billboard`.  
- Start size: 0.1–0.35, tuned by effect.  
- Fire visuals: warm gradient (orange → yellow), startSpeed 0.2–0.6.  
- Smoke visuals: darker gradient, longer lifetime, slower speed.  

### Bursts (EXPLOSION / HIT_SPARK / DUST_PUFF / IMPACT)
- `main.loop = false`.  
- `emission.bursts`: one burst with `repeatInterval = 0`.  
- **Default:** also set `emission.rateOverTime = 10` so sparks linger briefly instead of disappearing instantly.  
- If the prompt explicitly says *“burst only”*, then override with `rateOverTime = 0`.  
- `collision.enabled = false` by default (enable only if debris physics explicitly requested).  
- Optional short trails for sparks, short lifetime (0.2–0.5s).


### Trajectories (BULLET_TRAIL / PROJECTILE_TRAIL / FOAM_JET / WATER_JET)
- `main.simulationSpace = "World"`.  
- `collision.enabled = true`.  
- `collision.sendCollisionMessages = true`.  
- `collision.attachRelay = true`.  

---

## Particle Shooting Rule
For trajectory-style effects (BULLET_TRAIL, PROJECTILE_TRAIL, FOAM_JET, WATER_JET, or when prompt mentions “shoot”, “spray”, “emit forward”):  
- Effect emits forward from the object’s transform.  
- Always set `main.simulationSpace = "World"`.  
- Always set `collision.enabled = true`.  
- Always set `collision.sendCollisionMessages = true`.  
- Always set `collision.attachRelay = true`.  
- On collision, the target object’s `trigger()` may be invoked.  
- Not applicable to fluids (FIRE/SMOKE/WATER/FOAM/STEAM/MIST).  

---

## Category Override Rules
- If user specifies “no collision”, enforce `collision.enabled = false` regardless of category.  
- If user specifies “looping” or “one-shot”, override defaults accordingly.  
- If ambiguous, apply safe defaults (fluids loop, bursts one-shot, trajectories world-space + collision).  

---

## UI-Safe Keys for Particle Controls
These are the only valid dot-keys for `param_ui_particle`:  
- Booleans (Toggle): `main.loop`, `main.prewarm`, `main.playOnAwake`, `noise.enabled`, `trails.enabled`, `trails.dieWithParticles`.  
- Numbers (Slider): `duration`, `startSpeed`, `startSize`, `lifetime`, `emission.rateOverTime`, `emission.rateOverDistance`, `emission.bursts[0].count`, `noise.strength`, `noise.frequency`, `noise.scrollSpeed`, `noise.octaveCount`, `trails.lifetime`, `trails.ratio`, `renderer.sortingFudge`, `sizeOverLifetime.size.constant`, `rotationOverLifetime.z.constant`, `velocityOverLifetime.x.constant`, `velocityOverLifetime.y.constant`, `velocityOverLifetime.z.constant`, `velocityOverLifetime.speedModifier.constant`.  
- Strings (Dropdown): `renderer.renderMode` with options `[Billboard, StretchedBillboard, HorizontalBillboard, VerticalBillboard, Mesh]`.  

---

## Comment Annotation Rules
- The `comment` must explicitly include the inferred particle_category.  
- Example: `particle_category: FIRE`.  
- If overrides are applied, note them: `particle_category: FIRE, loop=false override`.  
- Comment must also embed UI cues such as `(slider)`, `(toggle)`, `(dropdown: [...])`.  

---

## Example
{
  "object_name": "FIRE_EFFECT@Effect",
  "lua_code": "",
  "particle_json": [
    {
      "effectName": "FIRE_EFFECT",
      "duration": 2.0,
      "startColor": { "r": 1, "g": 0.5, "b": 0, "a": 1 },
      "startSize": 0.25,
      "startSpeed": 0.4,
      "maxParticles": 120,
      "lifetime": 1.5,
      "main": {
        "gravityModifier": 0,
        "simulationSpace": "World",
        "scalingMode": "Local",
        "prewarm": false,
        "playOnAwake": false,
        "startLifetime": 1.5,
        "loop": true
      },
      "emission": {
        "rateOverTime": 12,
        "rateOverDistance": 0,
        "bursts": []
      },
      "velocityOverLifetime": {
        "enabled": true,
        "space": "World",
        "x": {"mode":"Constant","constant":0},
        "y": {"mode":"Constant","constant":0.6},
        "z": {"mode":"Constant","constant":0},
        "orbitalY": 0,
        "speedModifier": {"mode":"Constant","constant":1}
      },
      "colorOverLifetime": {
        "enabled": true,
        "gradient": {
          "colorKeys": [
            {"time":0, "color":{"r":1,"g":0.5,"b":0,"a":1}},
            {"time":1, "color":{"r":1,"g":1,"b":0,"a":0}}
          ],
          "alphaKeys": [
            {"time":0,"alpha":1},
            {"time":1,"alpha":0}
          ]
        }
      },
      "noise": {
        "enabled": true,
        "strength": 0.3,
        "frequency": 0.2,
        "scrollSpeed": 0.15,
        "octaveCount": 2,
        "quality": "Medium"
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
  "param_ui_lua": [],
  "comment": "Standalone particle effect (particle_category: FIRE). Looping by default. Includes duration (slider) and loop (toggle).",
  "created_at": "2025-08-27T19:00:00Z"
}

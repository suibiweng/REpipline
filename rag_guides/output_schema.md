# OUTPUT SCHEMA GUIDE

This guide defines the authoritative JSON structure that every generation must follow.  
All fields are required unless marked optional (`?`).  
No extra fields are allowed.

---

## TOP-LEVEL OBJECT

- `object_name` : string  
  - Must be ALL CAPS WITH UNDERSCORES.  
  - For particle-only: `<EFFECTNAME>@EFFECT`.  
- `created_at` : string  
  - ISO-8601 UTC (e.g., `"2025-08-27T21:30:00Z"`).  
- `lua_code` : string  
  - Escaped with `\n` and `\t` for JSON safety.  
- `particle_json` : array of Enhanced V2 particle effects.  
- `param_ui_lua` : array of UI definitions for Lua globals.  
- `param_ui_particle` : array of UI definitions for particle controls.  
- `comment` : string explanation of behavior, including UI cues.

---

## PARTICLE_JSON (ENHANCED V2 ONLY)

Each entry:
- `effectName`: string (ALL CAPS WITH UNDERSCORES).  
- `main`:
  - `gravityModifier`: number  
  - `simulationSpace`: enum ["Local","World"]  
  - `scalingMode`: enum ["Local","Hierarchy","Shape"]  
  - `prewarm`: boolean  
  - `playOnAwake`: boolean  
  - `duration`: number  
  - `startColor`: { r: number, g: number, b: number, a: number }  
  - `startSize`: number  
  - `startSpeed`: number  
  - `startLifetime`: number  
  - `maxParticles`: number  
  - `loop`: boolean  
- `shapeModule`:
  - `type`: enum ["Cone","Sphere","Hemisphere","Box","Circle"]  
  - `angle`: number  
  - `radius`: number  
  - `arc`: number  
  - `position`: { x: number, y: number, z: number }  
- `emission`:
  - `rateOverTime`: number  
  - `rateOverDistance`: number  
  - `bursts`: array of { time: number, count: number, cycleCount: number, repeatInterval: number }  
- `velocityOverLifetime`:
  - `enabled`: boolean  
  - `space`: enum ["Local","World"]  
  - `x`, `y`, `z`, `speedModifier`: MinMaxCurve objects  
  - `orbitalY`: number  
- `colorOverLifetime`:
  - `enabled`: boolean  
  - `gradient`: { colorKeys: [ { time:number, color:{r,g,b,a} } ], alphaKeys: [ { time:number, alpha:number } ] }  
- `sizeOverLifetime`:
  - `enabled`: boolean  
  - `separateAxes`: boolean  
  - `size`: MinMaxCurve  
- `rotationOverLifetime`:
  - `enabled`: boolean  
  - `separateAxes`: boolean  
  - `z`: MinMaxCurve  
- `noise`:
  - `enabled`: boolean  
  - `strength`: number  
  - `frequency`: number  
  - `scrollSpeed`: number  
  - `octaveCount`: number  
  - `quality`: enum ["Low","Medium","High"]  
- `trails`:
  - `enabled`: boolean  
  - `lifetime`: number  
  - `ratio`: number  
  - `dieWithParticles`: boolean  
- `renderer`:
  - `renderMode`: enum ["Billboard","StretchedBillboard","HorizontalBillboard","VerticalBillboard","Mesh"]  
  - `materialName`: string  
  - `sortingFudge`: number  
- `collision`:
  - `enabled`: boolean  
  - `type`: enum ["World","Planes"]  
  - `mode`: enum ["3D","2D"]  
  - `collidesWithMask`?: number  
  - `collidesWithLayers`?: [string]  
  - `sendCollisionMessages`: boolean  
  - `attachRelay`: boolean  
  - `dampen`: number  
  - `bounce`: number  
  - `lifetimeLoss`: number  
  - `minKillSpeed`: number  
  - `radiusScale`: number  
  - `quality`: enum ["Low","Medium","High"]  
  - `voxelSize`: number  
  - `maxCollisionShapes`: number  
  - `enableDynamicColliders`: boolean  
  - `multiplyColliderForceByParticleSize`: boolean  

---

## PARAM_UI_LUA

Each entry:  
- `name`: string (Lua global)  
- `type`: enum ["Slider","Toggle","InputField"]  
- `min`: number (if Slider)  
- `max`: number (if Slider)  
- `default`: number | boolean | string  
- `options`: [string] (if Dropdown, optional)  

---

## PARAM_UI_PARTICLE

Each entry:  
- `effectName`: string (must match a particle_json entry)  
- `label`: string (format: "EFFECTNAME: key")  
- `key`: string (UI-safe property path, e.g. "main.loop")  
- `type`: enum ["Slider","Toggle","Dropdown"]  
- `min`: number (if Slider)  
- `max`: number (if Slider)  
- `default`: number | boolean | string  
- `options`: [string] (if Dropdown)  

---

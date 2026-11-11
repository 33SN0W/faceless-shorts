# Format 2: Deep Dive 3D (`deep-dive`)

**Role in 33SN0W:** Original, cinematic 3D scientific & biological visualization.

## Use Cases
- Human body explainers & internal physiology
- "What happens if you swallow / inhale / touch something?"
- Dangerous insects, venoms, and extreme animals
- Scientific experiments & physics edge cases
- Strange biological phenomena & hypothetical physical scenarios

## Visual Direction
- **Three-World Progression:** Move dynamically across (A) **Real World** (warm sunlit environment + stylized SDF-sculpted `Human` figure), (B) **X-Ray Cutaway** (`xrayStage` + transparent cyan glass body revealing glowing organs/skeleton), and (C) **Macro Internal Journey** (`vessel`, blood cells, organs, procedural SDF meshes).
- **Original Identity:** Sculpt original procedural geometry (`src/core/sdf.js`: `sphere`, `ellipsoid`, `capsule`, `smin/ssub`, surface-net meshes). **Never** copy another creator's signature character models, framing, or scripts.
- **No Gore Policy:** Represent injury, venom, or internal stress via x-ray highlights, red warning pulses, color shifts, and clean anatomical diagrams—never graphic wounds.
- **Camera Language:** Macro tracking shots, shallow DOF (`aperture 0.003–0.006`), smooth continuous flight along physiological pathways.

## Narrative Pacing & Audio
- **Duration:** `30–45 s` (24 fps or 30 fps).
- **Shape:** Visceral "What happens if…?" hook → external action → x-ray transition → macro internal mechanism → biological escalation → recovery/twist.
- **Default Voice & Music:** `am_michael` (`1.0x`), `"tension"` (body/danger) or `"bed"` (curiosity) + `inhale`, `heartbeat`, `bubbles`, `sizzle`, `alarm`.

## Art Style Compatibility
- Best with: `cgi-motion`, `glow-sketch`, `ps2-retro`, `pixel-art`, `comic-art`, `chalkboard`, `explainer-2d`.

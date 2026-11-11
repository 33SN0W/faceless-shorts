# Art Style 08: CGI Motion (`cgi-motion`)

**Runtime ID:** `"cgi-motion"` (`art_style.js`)

## Visual Specification
- **Colour Palette:** High-dynamic-range cinematic palette — rich warm key highlights `#FFE4C4`, cool blue shadow fill `#3A5E8C`, deep cinematic contrast, selective crimson/cyan focal glows.
- **Lighting:** Studio 3-point PBR lighting (warm directional key with soft PCF shadows, cool rim light, hemisphere bounce, volumetric bloom).
- **Character Design:** Smooth sculpted 3D forms (`sdf.js` / `Human`) or crisp dimensional figures with soft depth-of-field isolation.
- **Environment Design:** Detailed layered 3D sets with realistic depth blur (`aperture 0.002–0.005`), reflective materials, and atmospheric rim lighting.
- **Camera Language:** Smooth cinema dolly pushes, macro sweeps, rack-focus transitions between foreground and background.
- **Texture & Materials:** Full native resolution (`1.0`), ACES tone mapping, soft bloom, subtle radial studio vignette, cinematic contrast (`1.12`) and saturation (`1.15`).
- **Animation Characteristics:** Fluid 30 fps continuous motion, realistic acceleration/deceleration curves (`eio`).
- **Scene Transitions:** Smooth dissolves, light-bloom cuts, clean match-moves.
- **Typography & Subtitle Compatibility:** Crisp white `Inter Black` with soft cinematic drop shadow + warm gold `#FFD43B` key word, `y = 1400`.
- **Negative Prompts & Unwanted Artifacts:** Avoid flat unlit plastic looks, harsh pixelated edges, blown-out bloom clipping over faces, or static locked-off tripods.

# Art Style 04: PS2 Retro 3D (`ps2-retro`)

**Runtime ID:** `"ps2-retro"` (`art_style.js`)

## Visual Specification
- **Colour Palette:** Early-2000s sixth-generation console palette — slightly moody saturated midtones, warm amber `#E8B04B`, muted teal `#4A8B8C`, deep navy `#1C2538`, crisp dithered shadows.
- **Lighting:** Vertex-style directional lighting with soft nostalgic bloom, limited dynamic range, and gentle CRT phosphor warmth.
- **Character Design:** Chunky stylized low-poly / crisp geometric forms; unmistakable primary colors and expressive bold silhouettes.
- **Environment Design:** Crisp low-resolution painted textures (`270×480` internal raster feel), nostalgic city blocks, corridors, and dramatic atmospheric fog.
- **Camera Language:** Third-person follow cams, dramatic low-angle hero shots, quick whip-pans reminiscent of classic early-2000s cutscenes.
- **Texture & Materials:** `270×480` framebuffer downscale + 4×4 Bayer ordered color dithering + subtle CRT scanlines (`alpha 0.06`).
- **Animation Characteristics:** Snappy 30 fps game-cutscene timing, bold idle sways, punchy action beats.
- **Scene Transitions:** Hard cutscene fades, CRT flash cuts.
- **Typography & Subtitle Compatibility:** Heavy arcade/console sans (`Inter Black`) with thick dark shadow box or classic outline, gold `#FFD43B` emphasis, `y = 1360`.
- **Negative Prompts & Unwanted Artifacts:** Avoid modern hyper-realistic PBR gloss, soft vector minimalism, or ultra-tiny unreadable UI strings inside the 270×480 raster pass.

# Art Style 01: Pixel Art (`pixel-art`)

**Runtime ID:** `"pixel-art"` (`art_style.js`)

## Visual Specification
- **Colour Palette:** 16-bit SNES/GBA high-contrast palette — crisp primaries `#E63946`, `#457B9D`, `#F4A261`, `#2A9D8F`, deep midnight ink `#14121D`, highlight cream `#FFF3D6`. Color channels quantized to 32-level steps.
- **Lighting:** Hard-edged stepped directional shading (no soft airbrushed gradients); bold daylight or crisp neon night contrast.
- **Character Design:** Chunky silhouette readability even at `180×320` grid scale; distinct hats, colors, and bold pixel outlines so characters remain legible at low resolution.
- **Environment Design:** Simplified blocky architecture, crisp repeating tile patterns (bricks, grass, wood planks), uncluttered horizons.
- **Camera Language:** Clean pans, stepped zoom punches, and discrete snap cuts; avoid micro-jitter subpixel pans.
- **Texture & Materials:** Nearest-neighbor pixel grid (`imageSmoothingEnabled = false` at `180×320` internal buffer upscaled 6× to `1080×1920`). Zero anti-aliasing blur on scene art.
- **Animation Characteristics:** Crisp 15 fps stepped motion option, snappy overshoot pops, arcade bounce curves.
- **Scene Transitions:** Crisp flash cuts, pixel wipe/iris-out transitions.
- **Typography & Subtitle Compatibility:** Monospace/arcade heavy uppercase (`FreeMono` / `Inter Black`), crisp pixel-aligned hard outline (`#14121D`), gold/amber `#FFD43B` highlight word, safe zone `y = 1340`.
- **Negative Prompts & Unwanted Artifacts:** Avoid soft anti-aliased fuzzy edges, muddy realistic photo gradients, microscopic unreadable 1px text inside the pixelated buffer, or mixels (inconsistent pixel sizes inside the scene layer).

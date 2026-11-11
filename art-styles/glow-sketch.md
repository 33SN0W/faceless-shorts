# Art Style 03: Glow Sketch (`glow-sketch`)

**Runtime ID:** `"glow-sketch"` (`art_style.js`)

## Visual Specification
- **Colour Palette:** Obsidian deep void `#060913`, primary neon cyan `#00E5FF`, electric magenta `#FF2E93`, radiant amber `#FFB800`, crisp ice white `#EAF8FF`.
- **Lighting:** Self-luminous emissive stroke lighting with radial bloom halation against pitch-dark space.
- **Character Design:** Luminous glowing edge contours on dark silhouettes; expressive glowing eyes/pupils and highlighted accessories.
- **Environment Design:** Wireframe/neon contour rooms, glowing anatomical tubes or crime-scene outlines emerging out of dark void.
- **Camera Language:** Smooth macro tracking glides, dramatic slow push-ins, subtle orbital sweeps that emphasize luminous depth.
- **Texture & Materials:** Real-time edge extraction on `360×640` buffer blended additively (`lighter`) with blurred glow halos over deep void `#060913`.
- **Animation Characteristics:** Fluid neon pulse breathing (`sin(t)` glow intensity), fast streak motion, smooth easing.
- **Scene Transitions:** Dark fade flashes, neon bloom surge transitions.
- **Typography & Subtitle Compatibility:** Crisp white `Inter` / `FreeMono` with glowing cyan/amber highlight word and dark outer stroke so captions stay sharp against bloom, `y = 1360`.
- **Negative Prompts & Unwanted Artifacts:** Avoid washed-out daytime pastel backgrounds, muddied gray fills, blown-out white clipping over faces, or messy overlapping neon lines that obscure silhouettes.

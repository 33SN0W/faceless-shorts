# Art Style 12: Claymation (`claymation`)

**Runtime ID:** `"claymation"` (`art_style.js`)

## Visual Specification
- **Colour Palette:** Tactile sculpted modeling-clay palette — warm terracotta `#D86E51`, butter yellow `#F2C64B`, sage green `#74A86D`, sky putty `#7BAED4`, matte cream `#F5EBD8`, dark clay ink `#2C2224`.
- **Lighting:** Warm miniature tabletop softbox lighting with soft diffused shadows and subtle miniature tilt-shift depth blur.
- **Character Design:** Rounded plump silhouettes, matte clay surface sheen, expressive sculpted brow/mouth swaps.
- **Environment Design:** Handmade miniature diorama sets, soft matte cardboard/clay surfaces, cozy shallow miniature depth of field.
- **Camera Language:** Tabletop miniature framing, deliberate stop-motion stepped pans, tight close-ups on sculpted faces.
- **Texture & Materials:** **12 fps stop-motion time stepping** (`quantizeTime(t, 12)`) so every motion snaps authentically like clay frames! Plus pre-rendered tactile clay-fingerprint micro-bump texture overlay (`soft-light`, `alpha 0.14`) + warm matte color grade (`saturate(1.14) contrast(1.06)`).
- **Animation Characteristics:** Authentic `12 fps` ("on twos") stop-motion stepped animation while exporting smooth 30 fps MP4!
- **Scene Transitions:** Tactile hard cuts, miniature wipe transitions.
- **Typography & Subtitle Compatibility:** Rounded heavy `Inter Black` cream/white with soft chocolate-clay outline `#2C2224`, warm yellow `#F2C64B` key word, `y = 1360`.
- **Negative Prompts & Unwanted Artifacts:** Avoid silky 60 fps CGI interpolation smoothness, sharp razor-thin neon lines, or harsh metallic chrome reflections.

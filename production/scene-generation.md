# Production: Scene Generation (Format × Art Style Integration)

## How Formats and Art Styles Combine
1. **Storytelling Format** (`script.json` `"format"`) picks the base engine (`tall-tale`, `deep-dive`, `inside-out`, `stick-story`, `night-file`, `paper-atlas`) — providing the 3D worlds, SDF organs, stick figures, cut-paper assets, or dark crime rooms.
2. **Art Style** (`script.json` `"artStyle"`) loads `src/core/art_style.js` and transforms:
   - **Time stepping** (`timeStep`, e.g. `12 fps` stop-motion quantization for `claymation`, `15 fps` for `pixel-art`).
   - **3D Engine Look Params** (for Three.js formats: bloom, DOF, exposure, grain, saturation overrides).
   - **Post-Processing Pass** (pixelation grid, Bayer dithering, halftone dots, blackboard chalk extraction, neon glow edges, watercolor paper wash, 16mm film grain, LEGO stud overlay) applied right after `sh.draw(...)`.
   - **Subtitle Theme & Safe Zones** applied cleanly on top so captions remain 100% tack-sharp.

## Creative Direction Modes (`scripts/studio.py`)
- **Explicit:** `--format deep-dive-3d --art-style glow-sketch`
- **Auto:** `studio.py recommend --topic "..."` chooses optimal format & art style for the topic.
- **Random:** `studio.py recommend --mode random` selects an untried `(format, artStyle)` pairing.
- **Reference-based:** `studio.py recommend --mode reference --ref sample.png` extracts palette, brightness, contrast, saturation, and edge sharpness via `ffmpeg + numpy` to generate a custom `artStyleConfig` JSON.

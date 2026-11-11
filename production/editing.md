# Production: Editing & Export (`capture.mjs` + `mix.py`)

## Audio Engineering (`tools/mix.py`)
- **Voice Priority:** Spoken narration normalized to `-19 dBFS` RMS.
- **Music Ducking:** Procedural beds (`bed`, `bounce`, `tension`) or custom royalty-free tracks sit at `-24 dBFS` baseline and smoothly duck by up to `55%` whenever voice energy is present.
- **Procedural Sound Effects (25 cues):** `whoosh`, `slide`, `pop`, `plop`, `gulp`, `boing`, `bubbles`, `sizzle`, `sparkle`, `thud`, `slam`, `tock`, `zip`, `alarm`, `inhale`, `heartbeat`, `ding`, `chirp`, `chug`, `stamp`, plus studio FX (`camera_shutter`, `page_flip`, `chalk`, `synth_swell`, `glitch_pop`).
- **Master Output:** Soft-clipped & peak-limited to `-1.0 dBFS`, `48000 Hz` stereo WAV (`data/mix.wav`).

## Video Encoding (`tools/capture.mjs`)
- **Default Specs:** `1080×1920` (9:16), `30 fps` (or `24 fps` for heavy 3D / vintage), `libx264`, `-profile:v high -level 4.1`, `-pix_fmt yuv420p`, `-crf 18`, `-c:a aac -b:a 192k -ar 48000`, `-movflags +faststart`.
- **Configurable Resolution & FPS:** `node tools/capture.mjs video renders/out.mp4 --fps 30 --res 1080x1920` (or `720x1280` for quick drafts).
- **Optional Looping:** Connect the final line/camera pose back to Shot 1 only when narratively seamless (flagged `"loop": true` in `script.json` for A/B tracking in `analytics.py`).

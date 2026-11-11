# Production: Subtitles & Mobile Safe Zones (`captions.js` + `art_style.js`)

## Safe-Area Standard (YouTube Shorts + Instagram Reels)
Based on current platform UI overlays (`1080×1920` canvas):
- **Top Clearance:** `y >= 280` (avoids search/header/camera icons).
- **Bottom Clearance:** `y <= 1460` (avoids channel handle, title/description, audio bar, and scrubber).
- **Right Clearance:** `x <= 940` in lower third (avoids vertical Like/Comment/Share/Remix stack).
- **Caption Width:** `maxW <= 880 px` centered at `x = 520..540`, `y = 1320..1420`.

## Typography & Synchronization
- **Word Sync:** Driven by `faster-whisper` word timestamps (`data/words.json`). Chunks appear `0.03–0.05 s` prior to the spoken word with subtle pop-in overshoot (`eob`).
- **Chunk Sizing:** 1–3 words per beat; keyword highlighted with `*word` in the active Art Style's accent color (`#FFD43B`, `#00E5FF`, `#D9383A`, etc.).
- **Caption Styles (`script.json` `"captionStyle"`):** `"auto"` (matches Art Style), `"bold-outline"`, `"pill-bar"`, `"paper-strip"`, `"typewriter-mono"`.
- **Visual QA Verification:** Preview with `node tools/capture.mjs frames review/safe "1.5" --safe-zones` to render the translucent safe-zone guide grid on top of frames.

# Quality Assurance: Platform Compliance QA

Automated via `ffprobe` on rendered MP4 inside `qa_check.py`:
- **Dimensions & Aspect:** Exactly `1080×1920` (9:16), or configured vertical target (`720×1280`).
- **Video Codec & Pixel Format:** `h264` (`libx264`), `yuv420p` (`yuvj420p` flagged if incompatible), steady FPS (`24`, `30`, or `60`).
- **Audio Codec & Sample Rate:** `aac`, `48000 Hz`, 2 channels (stereo).
- **Web Streaming Faststart:** Checks MP4 atom header order (`moov` precedes `mdat` via `-movflags +faststart`).
- **Length & Size:** Duration `<= 60.0 s` (optimal Shorts/Reels window; hard cap `180 s`), file size `< 35 MB` for direct sharing (`< 250 MB` IG cap).
- **AI Disclosure Flag Assessment:** Evaluates `format` + `artStyle` + `voice` to advise whether YouTube's Altered/Synthetic Content checkbox applies (`required: false` for clearly stylized animation/cartoons unless realistic synthetic faces/events/voice-cloning are used).

## Overall Quality Score (`review/qa_report.json`)
`qa_check.py` scores Factual (20 pts), Story (20 pts), Visual (20 pts), Audio (20 pts), and Platform (20 pts) out of **100** and reports actionable pass/warn/fail items.

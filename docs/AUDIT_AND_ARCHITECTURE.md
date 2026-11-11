# 33SN0W AI Video Studio — Skill Audit, Research & Architecture

**Research & Audit Date:** 2026-11-11  
**Channel:** 33SN0W (YouTube Shorts & Instagram Reels)  
**Backup Location:** `~/faceless-shorts/_backup_skill_2026-11-11/`

---

## Part 1: Audit of the Existing Skill

### 1.1 Existing Pipeline & Components
The baseline skill in `~/Desktop/faceless-shorts` renders vertical 9:16 shorts 100% locally in code:
- **TTS Narration:** `scripts/voice.py` using Kokoro-82M (`kokoro-onnx`) at 24 kHz mono, grouping lines into complete sentences for natural intonation and finding inter-clause silence points for cuts.
- **Word-Level Alignment:** `scripts/words.py` using `faster-whisper` (`small.en`, `int8` CPU) with `SequenceMatcher` alignment against `script.json` (plus `scripts/estimate.py` for captions-only mode).
- **Visual Rendering:** Headless Google Chrome running Three.js WebGL (`tall-tale`, `deep-dive`, `night-file`) or HTML5 2D Canvas (`inside-out`, `stick-story`, `paper-atlas`), driven frame-by-frame via `window.OP` in `tools/capture.mjs` and piped as JPEG frames to `ffmpeg` (`libx264`, `-crf 18`, `yuv420p`, `aac 192k`, `-movflags +faststart`).
- **Audio Mixing:** `tools/mix.py` synthesizing procedural sound effects + procedural music beds (`bed`, `bounce`, `tension`) in `numpy`/`scipy`, normalizing narration to `-19 dBFS` and ducking music under speech.

### 1.2 Empirical Evaluation of the Three Existing Sample Videos
Inspected via `ffprobe`, `volumedetect`, `script.json`, `src/shots.js`, and QA contact sheets (`review/all.jpg`):

| Metric / Observation | `bank-for-a-dollar.mp4` | `eiffel-tower-sale.mp4` | `plane-on-street.mp4` |
|---|---|---|---|
| **Resolution / Codec** | 1080×1920 H.264 / AAC 48 kHz | 1080×1920 H.264 / AAC 48 kHz | 1080×1920 H.264 / AAC 48 kHz |
| **Duration / FPS / Size** | 40.80 s · 30 fps · 19.8 MB | 41.47 s · 30 fps · 23.1 MB | 38.33 s · 30 fps · 23.3 MB |
| **Audio Loudness** | Mean `-18.1 dB`, Peak `-1.0 dB` | Mean `-18.2 dB`, Peak `-1.0 dB` | Mean `-18.4 dB`, Peak `-1.1 dB` |
| **Storytelling & Hook** | Immediate 2s hook ($1 bank buy); clear escalation & payoff | Strong 2s hook (Eiffel Tower scrap sale); solid second-sale twist | Strong 2s bet hook; good two-act escalation & ending |
| **Visual Diversity** | **Identical Tall Tale 3D look** | **Identical Tall Tale 3D look** | **Identical Tall Tale 3D look** |
| **Identified Visual Flaws** | Early side-counter framing clipped characters; `DEMOLISH` / `LOAN DENIED` / `+$3M` stamps overlapped faces | `DEMOLITION?`, `FORGED MINISTRY SEAL`, `NO POLICE REPORT`, `SOLD TWICE!` stamps overlapped eyes/faces; hotel counter cropped dealers | `15-MINUTE BET`, `$100 FINE ONLY`, `2 YEARS LATER` overlapped heads/foreheads; tavern counter cropped characters |

### 1.3 Bottlenecks, Hardcoded Assumptions & Gaps
1. **Coupled Format & Art Style:** Each of the 6 formats hardcodes both storytelling structure and visual rendering style. You cannot combine `Tall Tale 3D` with `Comic Art`, or `Deep Dive 3D` with `Glow Sketch`.
2. **Repetitive Channel Risk (YouTube Inauthentic Content Policy):** All three sample videos use identical 2D-toon-on-3D-street aesthetics, identical `Inter Black` captions without keyword highlighting, and identical `"bounce"` audio. Scaling this unchanged risks triggering YouTube's *Inauthentic Content* (formerly *Repetitious Content*) monetization policy.
3. **Platform Safe-Zone Blindness:**
   - Existing `night-file` (`y=1560`), `paper-atlas` (`y=1640`), and `stick-story` (`y=1690`) place captions inside the bottom UI danger zones of YouTube Shorts (`y > 1540`) and Instagram Reels (`y > 1250`–`1480`).
   - 2D graphic overlays (`y=680–720`) lacked safe anchor lanes away from character faces.
4. **Inconsistent `tools/mix.py` Across Styles:** `tall-tale` had `ding`, `chirp`, `chug`, `stamp`, and `music_bounce()`, while the other 5 styles lacked them.
5. **Monolithic Prompt File (`SKILL.md`):** Mixed intake, research, scripting, rendering, QA, and Zapier upload into one 124-line file with no reusable character registry, storyboard schema, topic originality check, multi-axis QA scorer, metadata generator, or analytics feedback loop.

---

## Part 17: Pre-Implementation Research Summary (2026-11-11)

### Evidence-Based Platform & Technical Findings
1. **YouTube Shorts Analytics (`Viewed vs. Swiped Away` & `Engaged Views`):**
   - **Finding:** YouTube counts a public *View* the moment playback starts/replays, whereas *Engaged Views* count only viewers who stay past the opening seconds. **Viewed vs. Swiped Away** measures hook survival in the first 1–3 seconds (70%+ Viewed = strong viral signal; ≥70% Swiped Away stalls feed distribution).
   - **Sources:** YouTube Official Blog / Creator documentation & Shorts analytics references (checked 2026-11-11: https://blog.youtube, https://support.google.com/youtube).
   - **Category:** **Evidence-based**.
2. **YouTube Monetization (`Reused Content` & `Inauthentic Content`):**
   - **Finding:** YouTube renamed *Repetitious Content* to *Inauthentic Content* and evaluates channels holistically. Mass-produced, rigid-template videos with generic AI narration and minimal visual variation are ineligible for YPP. Meaningful human creative direction, varied visual styles, original research, and distinct storytelling per video are required.
   - **Sources:** YouTube Partner Program monetization policies (`support.google.com/youtube`, checked 2026-11-11).
   - **Category:** **Evidence-based**.
3. **YouTube Altered or Synthetic Content Disclosure:**
   - **Finding:** Realistic synthetic media (making real people appear to do/say things they didn't, realistic fake events, or realistic voice cloning of real people) must be disclosed via the YouTube Studio synthetic-content flag. Clearly stylized animation, cartoons, and production-assistant AI use do not require the realistic-media label unless covering sensitive real-world events in realistic style.
   - **Sources:** YouTube Help — Disclosing altered or synthetic content (`support.google.com/youtube`, checked 2026-11-11).
   - **Category:** **Evidence-based**.
4. **YouTube Shorts & Instagram Reels Specs and Safe Zones:**
   - **Finding:** Standard export is **1080×1920 (9:16)**, MP4 container, H.264 (`libx264`, High profile, `yuv420p`), AAC-LC stereo at `48000 Hz` (`128–192 kbps`), `-movflags +faststart`. YouTube Shorts supports up to 3 minutes; Instagram Reels UI overlays top ~269 px, bottom ~380–672 px, and right ~120 px. Keeping captions and vital overlays inside `x: 90..940, y: 280..1440` ensures legibility across both platforms.
   - **Sources:** YouTube Help upload guidelines, Instagram Creator best practices, FFmpeg H.264/AAC encoding documentation (checked 2026-11-11).
   - **Category:** **Evidence-based**.
5. **Local TTS & Alignment Pipeline (`kokoro-onnx` & `faster-whisper`):**
   - **Finding:** Kokoro-ONNX outputs 24 kHz mono audio; `tools/mix.py` resamples via FFmpeg/scipy to 48 kHz stereo to avoid mobile playback rate glitches. `faster-whisper` (`small.en`, `int8`) provides word-level timestamps (`word_timestamps=True`) for accurate subtitle sync.
   - **Sources:** `kokoro-onnx` & `faster-whisper` official repositories/docs (checked 2026-11-11).
   - **Category:** **Evidence-based**.

### Experimental & Creative Guidelines
- **Experimental (treat as testable hypotheses tracked in `analytics.py`):**
  - Seamless looping endings (connecting final line/visual back to Shot 1).
  - Duration tiers (Short `20–30s` vs. Standard `35–45s` vs. Extended `45–60s`) per niche.
  - Stop-motion `12 fps` frame-stepping (`claymation`) vs. full `30 fps` motion on retention.
- **Creative Preferences:**
  - 13 distinct Art Style palettes/filters (`pixel-art` through `watercolour`) for channel variety and 33SN0W brand evolution.
  - Upper-frame badge anchor (`y = 290..360`) to prevent face/caption occlusion.

---

## Proposed Modular Architecture (33SN0W AI Video Studio)

```
faceless-shorts/
├── SKILL.md                  # Concise orchestrator entrypoint
├── formats/                  # 6 Storytelling Formats (narrative + spatial structure)
├── art-styles/               # 13 Independent Art Styles (visual specs + shader/canvas presets)
├── research/                 # Discovery, 7-factor scoring, originality & multi-source verification
├── scripting/                # 3-hook engine, narrative architect, script validation
├── production/               # Storyboard, character consistency, voice, subtitles, editing
├── quality/                  # 5-axis automated QA (Factual, Visual, Audio, Story, Platform)
├── analytics/                # Performance tracking, learning loop, YPP monetization safeguards
├── styles/_shared/           # Unified art_style.js + capture.mjs + mix.py synced to all 6 engines
└── scripts/                  # setup, new_video, voice, words, estimate, studio, qa_check, analytics
```

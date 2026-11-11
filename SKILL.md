---
name: faceless-shorts
description: 33SN0W AI Short-Form Video Studio — research-driven, fully local, $0 vertical YouTube Shorts & Instagram Reels generator. Independently combines 6 Storytelling Formats (Tall Tale 3D, Deep Dive 3D, Inside Out, Stick Story, Night File 3D, Paper Atlas) with 13 Art Styles (Pixel Art, Chalkboard, Glow Sketch, PS2 Retro 3D, Comic Art, Flat Vector, Minimal Line, CGI Motion, LEGO World, Explainer 2D, Vintage Film, Claymation, Watercolour). Includes creative direction (explicit/auto/random/reference), fact-checked research & 7-factor topic scoring, hook/storyboard/character consistency engines, safe-zone captions, 5-axis automated QA, multi-platform metadata, analytics learning loop, and optional Zapier YouTube publishing.
---

# 33SN0W AI Short-Form Video Studio (`faceless-shorts`)

You produce original, verified, high-retention 9:16 vertical short-form videos (`1080x1920`, H.264/AAC) locally on the user's computer at $0 API cost — using procedural 3D WebGL + 2D Canvas animation, headless Chrome frame capture, FFmpeg, local Kokoro neural TTS, Faster-Whisper word timing, procedural numpy SFX/music beds, automated 5-axis QA, and an analytics learning loop.

- `SKILL` = `~/Desktop/faceless-shorts`
- Video projects live in `~/faceless-shorts/<short-name>/`
- Original backup of the v1 skill is preserved in `~/faceless-shorts/_backup_skill_2026-11-11/`.

---

## 1. Studio Modular Architecture

Read only the specific modules needed for the active production:

| Module | Directory / File | Purpose |
| :--- | :--- | :--- |
| **Formats (6)** | `formats/*.md` & `styles/<format>/STYLE.md` | Narrative grammar, shot pacing, camera & set rules |
| **Art Styles (13)** | `art-styles/*.md` & `styles/_shared/art_style.js` | Palette, shader/post-process, quantization & caption theme |
| **Research Engine** | `research/topic-discovery.md`, `fact-checking.md`, `source-management.md` | Topic discovery, originality checks, multi-source verification |
| **Script & Hooks** | `scripting/hook-generator.md`, `story-architect.md`, `scriptwriter.md` | 20–30s / 35–45s / 45–60s pacing, 3 hooks, anti-cliché rules |
| **Production** | `production/storyboard.md`, `character-consistency.md`, `scene-generation.md`, `voiceover.md`, `subtitles.md`, `editing.md` | 14-field storyboards, character lock sheets, TTS, safe-zone subs, render specs |
| **Quality Gates** | `quality/factual-qa.md`, `visual-qa.md`, `audio-qa.md`, `platform-qa.md` & `scripts/qa_check.py` | 5-axis automated QA scorecard (`0–100`) before delivery |
| **Analytics & Policy** | `analytics/performance-tracking.md`, `learning-engine.md`, `monetization-safeguards.md` & `scripts/analytics.py` | Anti-vanity retention loop & YT/IG monetization/disclosure rules |
| **Invocation Guide** | `docs/INVOCATION_GUIDE.md` | End-to-end command recipes & user prompt patterns |

---

## 2. Independent Format × Art Style System

Never force every story into Tall Tale 3D. Storytelling format (`styles/`) and visual Art Style (`styles/_shared/art_style.js`) are **independent axes** that combine freely:

### 6 Storytelling Formats
1. `tall-tale` (alias `tall-tale-3d`) — `formats/tall-tale-3d.md`: Funny true history, scams, loopholes, bizarre incidents (2D cartoon actors inside bright 3D miniature worlds).
2. `deep-dive` (alias `deep-dive-3d`) — `formats/deep-dive-3d.md`: Anatomy, "what happens if you swallow/experience X", extreme physics/biology (original 33SN0W scientific 3D visualization, X-ray & macro camera cutaways).
3. `inside-out` — `formats/inside-out.md`: Psychology, health, everyday science explainers (clean 2D anatomical/mechanical cutaways & animated diagrams).
4. `stick-story` — `formats/stick-story.md`: Survival scenarios, life hacks, "what would you do if?" (expressive stick figures & clear step-by-step demonstrations).
5. `night-file` (alias `night-file-3d`) — `formats/night-file-3d.md`: Unsolved mysteries, dark historical incidents, disappearances (moody 3D suspense & factual restraint — never sensationalize real victims).
6. `paper-atlas` — `formats/paper-atlas.md`: Ancient civilizations, historic voyages, battles, empires (layered paper cutouts & animated parchment maps).

### 13 Independent Art Styles
`pixel-art` · `chalkboard` · `glow-sketch` · `ps2-retro` · `comic-art` · `flat-vector` · `minimal-line` · `cgi-motion` · `lego-world` · `explainer-2d` · `vintage-film` · `claymation` · `watercolour` (plus `default` for pure format-native look).

---

## 3. Standard End-to-End Production Workflow

Follow this exact sequence unless the user asks for a quick draft:

### Step 1 — Research & Originality Gate (`scripts/studio.py`)
1. Discover & verify facts from `>=2` independent reputable sources (`research/fact-checking.md`). Never invent stats, quotes, dollar figures, or historical events.
2. Check channel originality against `~/faceless-shorts/` & analytics history:
   ```bash
   python3 "$SKILL/scripts/studio.py" check-originality --topic "<topic>"
   python3 "$SKILL/scripts/studio.py" score --topic "<topic>"
   ```
3. Choose Creative Direction (Explicit, Auto, Random, or `--reference <img/video>`):
   ```bash
   "$SKILL/scripts/py" "$SKILL/scripts/studio.py" recommend --topic "<topic>"
   ```

### Step 2 — Scaffold Project & Author Story/Consistency Assets
Create the workspace folder (all 6 formats accept `--art-style`, `--duration short|standard|extended`, `--title`, `--fps`):
```bash
bash "$SKILL/scripts/new_video.sh" <format> <short-name> --art-style <preset> --duration <tier> --title "<Title>"
```
This creates `script.json`, `research.json`, `characters.json`, and `storyboard.json`.
1. Fill `research.json` completely (`verification_status: "verified"`, every key claim backed by real corroborated URLs, plus `uncertain_or_disputed[]` when applicable).
2. Write 3 alternative hooks in `script.json` (`"hooks": [...]`), pick the sharpest non-cliché hook, and validate pacing (`short` 20–30s / `standard` 35–45s / `extended` 45–60s):
   ```bash
   python3 "$SKILL/scripts/studio.py" check-script "$PROJ"
   ```
3. Lock recurring silhouettes, palettes, proportions, and rules in `characters.json`, and map every narration line to the 14-field scene plan in `storyboard.json`.

### Step 3 — Voice, Timing & Procedural Scene Animation
```bash
cd "$PROJ"
"$SKILL/scripts/py" "$SKILL/scripts/voice.py" .
"$SKILL/scripts/py" "$SKILL/scripts/words.py" .
```
1. Edit `src/shots.js` (keeping characters & key captions inside the **YT Shorts + IG Reels Safe Zone**: `x: 70–940`, `y: 280–1470`, caption center `x ≈ 505, y ≈ 1380`).
2. Add SFX & music cues (`cues.push(...)`), generate mix & verify sync:
```bash
node tools/capture.mjs check --art-style <preset>
node tools/capture.mjs cues
"$SKILL/scripts/py" tools/mix.py .
```

### Step 4 — Contact Sheet Visual Review & Full Render
**MANDATORY:** Always render and inspect the contact sheet (`review/all.jpg`) using `read_file` BEFORE encoding the final MP4:
```bash
node tools/capture.mjs sheet review/all.jpg 2 --safe-zones
# Visually inspect review/all.jpg for overlap, cropping, contrast, safe zones, and character consistency!
node tools/capture.mjs video "renders/$(basename "$PWD").mp4"
```
(Optional flags on `capture.mjs`: `--art-style <preset>`, `--fps 30|60`, `--res 1080x1920`, `--safe-zones`, `--draft`.)

### Step 5 — Platform Metadata, 5-Axis QA Gate & Analytics Log
```bash
python3 "$SKILL/scripts/studio.py" metadata "$PROJ"
"$SKILL/scripts/py" "$SKILL/scripts/qa_check.py" "$PROJ"
python3 "$SKILL/scripts/analytics.py" log-video "$PROJ"
```
Fix any QA blockers (`black_frames_detected`, `silent_audio`, `wrong_aspect_ratio`, `banned_or_empty_hook`) before presenting or uploading.
If Zapier / YouTube publishing is configured and the user explicitly asks to upload, present `metadata.json` (`title_options`, `description`, `ai_synthetic_disclosure`) and upload after user confirmation. For local batch uploads directly from Mac via YouTube Data API v3 (using `~/.faceless-shorts/youtube_client_secrets.json` OAuth without external hosting), use `"$SKILL/scripts/py" "$SKILL/scripts/youtube_upload.py" <project...>` (supports `--dry-run`, `--auth-only`, `--privacy`, and `--publish-at` / `--stagger-hours`; see `docs/INVOCATION_GUIDE.md` Section 5).

---

## 4. Critical Studio Guardrails
- **Never** invent numbers, quotes, dates, or fake metrics in `research.json`, `metadata.json`, or `analytics.json`.
- **Never** open a hook with `"Hey guys"`, `"Welcome back"`, `"Today we are going to discuss"`, `"In this video"`, `"Let's dive in"`.
- **Never** sensationalize victims or fabricate details in `night-file` mysteries.
- **Never** place critical text/captions/faces in the top `y < 280`, bottom `y > 1470`, or right-hand button column `x > 940`.
- **Always** run `bash "$SKILL/scripts/selftest.sh"` after modifying shared engines or scripts to verify zero regressions.

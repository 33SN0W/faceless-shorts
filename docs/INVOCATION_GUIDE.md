# 33SN0W Studio Invocation Guide

Concrete workflows and command examples for invoking every mode of the upgraded `faceless-shorts` studio.

---

## 1. Choosing Visual Direction (4 Input Modes)

### A. Explicit Selection (Format × Art Style)
Prompt style: *"Create a 40s video about how Pepsi briefly became a naval power using Tall Tale 3D and Comic Art."*
```bash
bash scripts/new_video.sh tall-tale pepsi-navy --art-style comic-art --duration standard --title "The Day Pepsi Owned Warships"
```

### B. Automatic Selection (Topic-Driven)
Prompt style: *"Make a Short about what happens to your brain at 30,000 feet without cabin pressure."*
```bash
./scripts/py scripts/studio.py recommend --topic "What happens to your brain without cabin pressure at 30,000 feet"
# -> Automatically routes to deep-dive x glow-sketch (or cgi-motion), never forcing tall-tale!
```

### C. Random Experimentation
Prompt style: *"Surprise me with a fresh visual style combo for a bizarre historical law."*
```bash
./scripts/py scripts/studio.py recommend --topic "The 1924 ban on leaky umbrellas in London" --random
```

### D. Reference-Based Inspiration (`--reference`)
Prompt style: *"Make a video on the Bronze Age Collapse inspired by the look of this image/clip."*
```bash
./scripts/py scripts/studio.py recommend \
  --topic "Why Bronze Age civilizations collapsed in 50 years" \
  --reference /path/to/mood_reference.png
```
`studio.py` measures average RGB warmth, brightness, contrast, saturation, and edge density via `ffmpeg` + `numpy` and selects an original preset inspired by those visual properties without copying any third-party creator's characters or copyrighted brand.

---

## 2. Research, Originality & Script Validation

```bash
# 1. Check originality against existing ~/faceless-shorts/* and analytics history
python3 scripts/studio.py check-originality --topic "The 1919 Boston Molasses Flood"

# 2. Score topic viability (or pass explicit 1-10 ratings)
python3 scripts/studio.py score --topic "The 1919 Boston Molasses Flood" \
  --curiosity 9 --originality 8 --emotion 8 --shareability 8 --visual 9 --story 9 --reliability 9

# 3. Validate script hooks, tier duration & 14-field storyboard
python3 scripts/studio.py check-script ~/faceless-shorts/boston-molasses
```

---

## 3. Full Production & Render Pipeline

```bash
cd ~/faceless-shorts/<short-name>
SKILL=~/Desktop/faceless-shorts

# Voice + word timing
"$SKILL/scripts/py" "$SKILL/scripts/voice.py" .
"$SKILL/scripts/py" "$SKILL/scripts/words.py" .

# Validate animation & cues + generate SFX/music mix
node tools/capture.mjs check --art-style <preset>
node tools/capture.mjs cues
"$SKILL/scripts/py" tools/mix.py .

# Contact sheet review (with optional --safe-zones guide lines for layout QA)
node tools/capture.mjs sheet review/all.jpg 2 --safe-zones

# Full 1080x1920 master render (supports --fps 60, --res 1080x1920, --art-style <preset>)
node tools/capture.mjs video "renders/$(basename "$PWD").mp4" --fps 30
```

---

## 4. Metadata, 5-Axis QA Gate & Analytics

```bash
# Generate platform-tuned YT Shorts + IG Reels titles, captions, tags & disclosure note
python3 scripts/studio.py metadata ~/faceless-shorts/<short-name>

# Run automated 5-axis QA (Factual, Story, Audio, Visual, Platform) -> writes review/qa_report.json
./scripts/py scripts/qa_check.py ~/faceless-shorts/<short-name>

# Log build into ~/.faceless-shorts/analytics.json
python3 scripts/analytics.py log-video ~/faceless-shorts/<short-name> --hook-type visual_shock

# After publishing, import real retention & share data from YT Studio / IG Insights
python3 scripts/analytics.py import-metrics <short-name> \
  --views 18400 --engaged-views 12100 --stayed-to-watch 68.5 --avg-pct-viewed 94.2 --shares 310 --saves 420

# View channel summary & learning recommendations
python3 scripts/analytics.py summary
python3 scripts/analytics.py recommend
```

---

## 5. Local YouTube Shorts Batch Upload (`scripts/youtube_upload.py`)

Place your Google Cloud Desktop OAuth 2.0 JSON at `~/.faceless-shorts/youtube_client_secrets.json`, then authenticate once and upload directly from local MP4 + `metadata.json`:

```bash
# 1. Dry-run validation (checks MP4, QA pass >=65, metadata, tag limits)
./scripts/py scripts/youtube_upload.py pig-war-1859 timothy-dexter-fortune --dry-run

# 2. Authenticate once via browser OAuth (stores token in ~/.faceless-shorts/youtube_token.json)
./scripts/py scripts/youtube_upload.py --auth-only

# 3. Upload batch (supports --privacy private|unlisted|public or staggered schedule)
./scripts/py scripts/youtube_upload.py pig-war-1859 timothy-dexter-fortune --privacy private
./scripts/py scripts/youtube_upload.py pig-war-1859 timothy-dexter-fortune \
  --publish-at 2026-11-12T18:00:00Z --stagger-hours 24
```

---

## 6. Local Pre-Render Review & Control Web UI (`scripts/studio_ui.py`)

Launch the local loopback studio dashboard (`http://127.0.0.1:8765/`) to switch between 3 hooks, edit `script.json` cuts and captions, audition Kokoro voices live, inspect `review/all.jpg` safe-zone contact sheets, scrub MP4 previews, inspect 5-axis QA scores, track background jobs, and trigger 1-click Private uploads:

```bash
./scripts/py scripts/studio_ui.py --open
./scripts/py scripts/studio_ui.py --self-test   # Loopback HTTP API smoke test
```

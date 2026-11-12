# Product Design Specification (`33SN0W AI Short-Form Video Studio`)

**Perspective:** Product Manager & System Architect  
**Product Goal:** Enable a solo creator to ideate, research, animate, QA-verify, batch-upload, and optimize original 9:16 YouTube Shorts & Instagram Reels at **`$0.00` variable cost**, without triggering YouTube *Reused Content* or *Inauthentic Content* penalties.

---

## 1. Problem Statement & Target Persona

### Core Persona: The Solo Faceless Storyteller
Creators running factual/storytelling channels (`33SN0W`, `ShortsDaily`) face three compounding bottlenecks with typical AI video tools:
1. **Unit-Economics Trap:** SaaS video generators (`$30–$150/mo` + paid TTS + paid stock APIs + LLM tokens) destroy margins before a new Shorts channel monetizes.
2. **Template Fatigue & Demonetization Risk:** Most generators overlay TTS on scraped gameplay/stock clips (`Reused Content` / copyright strikes) or force every topic into one repetitive template (`Inauthentic Content`).
3. **Fragmented Last-Mile Publishing:** Switching between ChatGPT, ElevenLabs, CapCut, YouTube Studio uploads, hashtags, and analytics spreadsheets breaks daily publishing cadence.

### Product Thesis
If we run **100% local procedural animation, neural voice synthesis, automated safe-zone QA, and OAuth resumable YouTube batch upload** inside a single local studio (`$0.00` marginal cost per Short), creators gain predictable daily supply, crisp visual variety (`6` formats × `13` art styles), and clean monetization hygiene.

---

## 2. Jobs-to-be-Done (JTBD) & "The ProdMan Way" Funnel

Every screen and CLI step maps directly to one stage of the creator funnel:

| Stage | User Job ("When I…") | Studio Feature | Primary Success Signal | Guardrail / Counter-Metric |
| --- | --- | --- | --- | --- |
| **1. Ideate & Filter** | Want to brainstorm timely Shorts in niches I enjoy (`Horror`, `History`, `Scams`) | Prompt box + Genre filters + Batch draft counter (`Create`) | Originality score clear vs. existing catalog | Duplicate check blocks repeated topics |
| **2. Story & Voice** | Want to hear how the opener hooks attention before waiting on a full render | 3 alternative hooks, editable scene cuts & live **Kokoro-82M** voice audition (`Review`) | Crisp 1–3s premise without cliché intros | Script gate flags banned phrases & oversized cuts |
| **3. Visual QA** | Want to confirm captions/faces aren't covered by Shorts/Reels UI buttons | 9:16 phone player + **Live Safe-Zone Frame Overlay** + storyboard zoom grid | Zero text/face occlusion (`x: 70–940, y: 280–1470`) | `qa_check.py` fails `<65` / silent audio / black frames |
| **4. Package & Publish** | Want to push a full week's batch cleanly without cloud upload fees | Select `1..N` or `All` ready videos, schedule or upload `private` in 1 click (`Upload`) | Resumable upload + hashtags + source citations in Studio | Idempotent `upload_receipt.json` + daily YouTube quota telemetry |
| **5. Learn & Iterate** | Want to double down on formats viewers actually finish watching | Log Studio metrics (`Viewed %`, `Avg % Viewed`, `Shares`) into `analytics.py` (`Product`) | Higher `Stayed to Watch` & `Avg % Viewed` | Rejects empty vanity `views` without engagement |

---

## 3. North Star Metrics & Tradeoffs

### Metrics Framework
- **North Star Retention Signal:** `Viewed vs. Swiped Away` (`>= 70%`) × `Average % Viewed` (`>= 90%`) + `Shares / Saves per 1k Engaged Views`.
- **Operational Reliability:** `100/100` pre-upload QA pass rate across Audio Loudness (`-19 dBFS` speech target), Visual Safe Zones, and Factual Citations (`>= 2` independent sources).
- **Unit Cost:** **`$0.00` per rendered & uploaded Short** (local CPU/GPU + free YouTube Data API v3 upload quota).

### Key Product Tradeoffs
| Decision | Tradeoff Accepted | Why It Wins for This Product |
| --- | --- | --- |
| **Local Chrome + Kokoro + Whisper** instead of cloud APIs | Renders take ~30–60s on Mac CPU/GPU instead of cloud GPUs; requires ~0.9 GB one-time weights | `$0.00` perpetual COGS, zero API rate limits, private offline assets. |
| **Pre-render Draft Approval** instead of blind auto-publish | User reviews hooks/sources/frames before pushing live | Prevents factual hallucinations, off-frame captions, and wasted daily API upload quota. |
| **Desktop OAuth + `private` staging** instead of unverified public push | First OAuth needs one Test User login; Testing tokens refresh every 7 days | Bypasses slow YouTube API compliance audit so creators ship immediately via YouTube Studio flip. |
| **Original Procedural Vectors** instead of scraped `yt-dlp` clips | Higher engineering complexity per format engine (`6` formats × `13` styles) | Eliminates copyright strikes & protects YouTube Partner Program eligibility. |

---

## 4. Visual & Interaction Design System

The Studio Web UI ([`scripts/studio_ui.py`](../scripts/studio_ui.py)) synthesizes dark-mode desktop ergonomics from four product benchmarks over an Apple obsidian base:
- **Apple Dark Graphite Foundation:** `#08090a`–`#1c1c1e` layered dark surfaces, frosted glass top toolbar (`backdrop-filter: blur(26px)`), SF Pro typography, and clear plain-English status pills (`Video Rendered`, `Framing Verified`).
- **Linear (`linear.app`):** Deep obsidian luminance ladder (`#08090a` → `#0f1012` → `#17181c`), `1px` specular hairline dividers, tight `-0.03em` display tracking, Bento metric tiles, and an instant **`⌘K` Command Spotlight** modal for keyboard navigation.
- **Stripe (`stripe.com/in`):** Ultra-subtle slow animated ambient aurora gradient ribbon (`635bff` / `00d4ff` / `7166ee` at restrained ~`11%` opacity behind obsidian glass) signaling active studio atmosphere without reducing text contrast.
- **Tailwind CSS (`tailwindcss.com`):** Crisp `36px` blueprint coordinate grid faded radially toward screen edges (`mask-image: radial-gradient`), giving technical structure behind cards.
- **Cuberto (`wickret.cuberto.com`):** Cursor-tracking radial hover spotlight inside Bento cards (`--mx`, `--my`), fluid spring easing (`cubic-bezier(0.16, 1, 0.3, 1)`), and smooth `viewEnter` state transitions (`prefers-reduced-motion` compliant).

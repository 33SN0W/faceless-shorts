#!/usr/bin/env python3
"""33SN0W Studio — Minimalist Dark Apple-Styled Creator Dashboard.

Prompt video ideas with genre filters, generate/audition scripts visually,
review rendered Shorts side-by-side with plain-English checks, and batch upload
any chosen number of videos to YouTube with one click.

Usage:
  ./scripts/py scripts/studio_ui.py [--port 8765] [--open]
  ./scripts/py scripts/studio_ui.py --self-test
"""
import argparse
import datetime
import functools
import io
import json
import os
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
import wave
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

SKILL_DIR = Path(__file__).resolve().parent.parent
FACELESS_HOME = Path(os.environ.get("FACELESS_HOME", Path.home() / ".faceless-shorts"))
DEFAULT_PROJECTS_DIR = Path.home() / "faceless-shorts"
JOBS_STORE = FACELESS_HOME / "studio_jobs.json"
PY_WRAPPER = SKILL_DIR / "scripts" / "py"

VOICES = [
    ("am_michael", "Michael (US Male · Calm Narrator)"),
    ("am_puck", "Puck (US Male · Energetic)"),
    ("am_fenrir", "Fenrir (US Male · Deep & Dramatic)"),
    ("am_onyx", "Onyx (US Male · Low Thriller)"),
    ("af_heart", "Heart (US Female · Warm)"),
    ("af_bella", "Bella (US Female · Bright)"),
    ("af_nicole", "Nicole (US Female · Intimate)"),
    ("bm_george", "George (UK Male · Documentary)"),
    ("bm_fable", "Fable (UK Male · Storyteller)"),
    ("bf_emma", "Emma (UK Female · Crisp)"),
]
VALID_VOICES = {v[0] for v in VOICES}

GENRE_FILTERS = [
    {
        "id": "history",
        "label": "History",
        "format": "stick-story",
        "artStyle": "default",
        "music": "bounce",
        "voice": "am_michael",
        "hashtags": ["#history", "#weirdhistory", "#truestory"],
        "samples": [
            "The city that accidentally declared war on an ocean",
            "How a typo changed the borders of an entire town",
        ],
    },
    {
        "id": "horror",
        "label": "Horror & Mysteries",
        "format": "night-file",
        "artStyle": "vintage-film",
        "music": "tension",
        "voice": "am_fenrir",
        "hashtags": ["#mystery", "#unsolved", "#darkhistory"],
        "samples": [
            "The lighthouse crew that vanished with soup still warm on the table",
            "Why nobody could explain the repeating ocean signal",
        ],
    },
    {
        "id": "events",
        "label": "Weird Events",
        "format": "tall-tale",
        "artStyle": "comic-art",
        "music": "bounce",
        "voice": "am_puck",
        "hashtags": ["#weirdevents", "#historyfacts", "#bizarre"],
        "samples": [
            "The day thousands of people gathered to watch a train crash on purpose",
            "How an entire town got tricked by a fake meteor sighting",
        ],
    },
    {
        "id": "scams",
        "label": "Scams & Loopholes",
        "format": "tall-tale",
        "artStyle": "default",
        "music": "bounce",
        "voice": "am_michael",
        "hashtags": ["#scam", "#loophole", "#truestory"],
        "samples": [
            "The loophole that let one flyer collect lifetime pudding points",
            "How a fake country got sold to real investors in London",
        ],
    },
    {
        "id": "science",
        "label": "Science & Body",
        "format": "deep-dive",
        "artStyle": "glow-sketch",
        "music": "bed",
        "voice": "af_heart",
        "hashtags": ["#science", "#humanbody", "#explained"],
        "samples": [
            "What happens inside your eardrums seconds before pressure pops them",
            "Why deep-sea creatures glow blue instead of red",
        ],
    },
    {
        "id": "survival",
        "label": "Survival",
        "format": "stick-story",
        "artStyle": "default",
        "music": "tension",
        "voice": "am_michael",
        "hashtags": ["#survival", "#safetytips", "#whatwouldyoudo"],
        "samples": [
            "What you should actually do if your car sinks in deep water",
            "Why running downhill from a rockslide gets people trapped",
        ],
    },
    {
        "id": "empires",
        "label": "Empires & Battles",
        "format": "paper-atlas",
        "artStyle": "watercolour",
        "music": "bed",
        "voice": "bm_george",
        "hashtags": ["#ancienthistory", "#empires", "#maps"],
        "samples": [
            "How one narrow mountain pass halted an army of tens of thousands",
            "The ancient sea trade route that moved spices across three continents",
        ],
    },
]
FILTER_MAP = {f["id"]: f for f in GENRE_FILTERS}

LOOK_PRESETS = [
    ("auto", "Smart Match (Auto-Pick Best Look)"),
    ("stick-story:default", "Stick Figure Story (Clean 2D)"),
    ("tall-tale:default", "Tall Tale 3D (Cartoon Miniature)"),
    ("night-file:vintage-film", "Dark Mystery 3D (Moody Film)"),
    ("deep-dive:glow-sketch", "3D Science X-Ray (Glow Sketch)"),
    ("paper-atlas:watercolour", "Paper Atlas (Animated Maps)"),
    ("inside-out:explainer-2d", "Inside Out (Clean Infographic)"),
]

_KOKORO_LOCK = threading.Lock()
_KOKORO_INST = None


def read_json(path: Path, default=None):
    if default is None:
        default = {}
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def resolve_project_dir(projects_dir: Path, slug: str) -> Path:
    clean = str(slug or "").strip()
    if not clean or "/" in clean or "\\" in clean or clean in {".", ".."} or clean.startswith("_"):
        raise ValueError(f"Invalid project name: {slug!r}")
    root = projects_dir.resolve()
    target = (root / clean).resolve()
    if target.parent != root or not target.is_dir():
        raise FileNotFoundError(f"Video project not found: {clean}")
    return target


def find_master_mp4(proj: Path) -> Path | None:
    renders = proj / "renders"
    if not renders.is_dir():
        return None
    preferred = renders / f"{proj.name}.mp4"
    if preferred.exists():
        return preferred
    mp4s = [p for p in renders.glob("*.mp4") if "draft" not in p.stem and "selftest" not in p.stem]
    if not mp4s:
        return None
    mp4s.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return mp4s[0]


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return s[:48].strip("-") or f"short-{uuid.uuid4().hex[:6]}"


def synthesize_kokoro_wav(text: str, voice: str = "am_michael", speed: float = 1.0) -> bytes:
    """Synthesize a quick local voice preview WAV in memory via Kokoro-82M."""
    global _KOKORO_INST
    snippet = " ".join(str(text or "").split())[:420]
    if not snippet:
        raise ValueError("Enter a line or hook first to preview the voice.")
    if voice not in VALID_VOICES:
        voice = "am_michael"
    speed = max(0.65, min(1.5, float(speed or 1.0)))

    kdir = FACELESS_HOME / "kokoro"
    onnx_p = kdir / "kokoro-v1.0.onnx"
    voices_p = kdir / "voices-v1.0.bin"
    if not onnx_p.exists() or not voices_p.exists():
        raise FileNotFoundError("Voice files are not downloaded yet. Run setup.sh once.")

    from kokoro_onnx import Kokoro

    with _KOKORO_LOCK:
        if _KOKORO_INST is None:
            _KOKORO_INST = Kokoro(str(onnx_p), str(voices_p))
        lang = "en-gb" if voice.startswith("b") else "en-us"
        samples, sr = _KOKORO_INST.create(snippet, voice=voice, speed=speed, lang=lang)

    arr = np.asarray(samples, dtype=np.float64)
    peak = float(np.abs(arr).max()) if len(arr) else 0.0
    if peak > 1e-9:
        arr = arr / peak * 0.9
    pcm = (np.clip(arr, -1.0, 1.0) * 32767.0).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr or 24000))
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


class JobManager:
    """Thread-safe local job runner with clean persistent status."""

    def __init__(self, store_path: Path = JOBS_STORE, max_keep: int = 40):
        self.store_path = store_path
        self.max_keep = max_keep
        self._lock = threading.Lock()
        self._jobs: list[dict] = self._load()

    def _load(self) -> list[dict]:
        data = read_json(self.store_path, [])
        if not isinstance(data, list):
            return []
        now = datetime.datetime.now().isoformat(timespec="seconds")
        for job in data:
            if job.get("status") == "running":
                job["status"] = "interrupted"
                job["finished_at"] = now
        return data[: self.max_keep]

    def _save(self) -> None:
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            self.store_path.write_text(json.dumps(self._jobs[: self.max_keep], indent=2) + "\n")
        except Exception:
            pass

    def list_jobs(self, slug: str = "") -> list[dict]:
        with self._lock:
            items = [j for j in self._jobs if not slug or j.get("slug") == slug]
            return [dict(j) for j in items[:25]]

    def has_running_key(self, key: str) -> bool:
        with self._lock:
            return any(j.get("slug") == key and j.get("status") == "running" for j in self._jobs)

    def start(self, key: str, label: str, steps: list[tuple[str, list[str], Path]]) -> dict:
        if self.has_running_key(key):
            raise RuntimeError(f"Already running an action for '{key}'. Wait a moment.")
        job_id = uuid.uuid4().hex[:10]
        rec = {
            "id": job_id,
            "slug": key,
            "action": label,
            "status": "running",
            "started_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "finished_at": None,
            "exit_code": None,
            "log": [],
        }
        with self._lock:
            self._jobs.insert(0, rec)
            self._jobs = self._jobs[: self.max_keep]
            self._save()
        threading.Thread(target=self._run, args=(job_id, steps), daemon=True).start()
        return dict(rec)

    def _append_log(self, job_id: str, line: str) -> None:
        with self._lock:
            for j in self._jobs:
                if j["id"] == job_id:
                    j["log"].append(line)
                    j["log"] = j["log"][-140:]
                    break

    def _finish(self, job_id: str, status: str, exit_code: int) -> None:
        with self._lock:
            for j in self._jobs:
                if j["id"] == job_id:
                    j["status"] = status
                    j["exit_code"] = exit_code
                    j["finished_at"] = datetime.datetime.now().isoformat(timespec="seconds")
                    break
            self._save()

    def _run(self, job_id: str, steps: list[tuple[str, list[str], Path]]) -> None:
        code = 0
        try:
            for label, cmd, cwd in steps:
                self._append_log(job_id, f"Starting {label}...")
                proc = subprocess.Popen(
                    cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
                )
                assert proc.stdout is not None
                for raw in proc.stdout:
                    line = raw.rstrip("\r\n")
                    if line:
                        self._append_log(job_id, line)
                code = proc.wait()
                if code != 0:
                    self._append_log(job_id, f"Stopped: {label} returned code {code}.")
                    self._finish(job_id, "failed", code)
                    return
            self._append_log(job_id, "Finished cleanly.")
            self._finish(job_id, "completed", 0)
        except Exception as exc:
            self._append_log(job_id, f"Error: {exc}")
            self._finish(job_id, "failed", 1)


def summarize_project(proj: Path) -> dict:
    script = read_json(proj / "script.json", {})
    qa = read_json(proj / "review" / "qa_report.json", {})
    receipt = read_json(proj / "upload_receipt.json", {})
    meta = read_json(proj / "metadata.json", {})
    research = read_json(proj / "research.json", {})
    mp4 = find_master_mp4(proj)
    axes = qa.get("axes", {})
    return {
        "slug": proj.name,
        "title": script.get("title") or meta.get("youtube_shorts", {}).get("recommended_title") or proj.name.replace("-", " ").title(),
        "format": script.get("format", "stick-story"),
        "artStyle": script.get("artStyle", "default"),
        "genre": script.get("genreTags") or [],
        "durationTier": script.get("durationTier", "standard"),
        "line_count": len(script.get("lines", [])),
        "qa_score": qa.get("total_score"),
        "qa_passed": bool(qa.get("passed")),
        "audio_ok": (axes.get("audio", {}).get("score", 0) or 0) >= 15,
        "visual_ok": (axes.get("visual", {}).get("score", 0) or 0) >= 15,
        "story_ok": (axes.get("story", {}).get("score", 0) or 0) >= 15,
        "verified_sources": research.get("verification_status") == "verified",
        "has_sheet": (proj / "review" / "all.jpg").exists(),
        "has_mp4": mp4 is not None,
        "mp4_mb": round(mp4.stat().st_size / (1024 * 1024), 2) if mp4 else None,
        "has_narration": (proj / "data" / "narration.wav").exists(),
        "uploaded": bool(receipt.get("video_id")),
        "youtube_url": receipt.get("url"),
        "privacy_status": receipt.get("privacy_status"),
        "recommended_title": meta.get("youtube_shorts", {}).get("recommended_title"),
        "description": meta.get("youtube_shorts", {}).get("description"),
        "mtime": proj.stat().st_mtime,
    }


def list_projects(projects_dir: Path) -> list[dict]:
    if not projects_dir.exists():
        return []
    out = []
    for child in projects_dir.iterdir():
        if not child.is_dir() or child.name.startswith((".", "_")):
            continue
        if (child / "script.json").exists():
            out.append(summarize_project(child))
    out.sort(key=lambda item: item["mtime"], reverse=True)
    return out


def run_script_check(target_path: Path) -> dict:
    res = subprocess.run(
        [sys.executable, str(SKILL_DIR / "scripts" / "studio.py"), "check-script", str(target_path), "--json"],
        capture_output=True, text=True,
    )
    if res.stdout.strip():
        try:
            return json.loads(res.stdout)
        except Exception:
            pass
    return {"ok": res.returncode == 0, "issues": [res.stderr.strip()] if res.returncode else [], "warnings": []}


def choose_direction(prompt: str, filter_ids: list[str], look: str) -> dict:
    if look and look != "auto" and ":" in look:
        fmt, art = look.split(":", 1)
        primary = FILTER_MAP.get(filter_ids[0]) if filter_ids else None
        return {
            "format": fmt,
            "artStyle": art,
            "music": (primary or {}).get("music", "bounce"),
            "voice": (primary or {}).get("voice", "am_michael"),
        }

    if filter_ids:
        primary = FILTER_MAP.get(filter_ids[0], GENRE_FILTERS[0])
        return {
            "format": primary["format"],
            "artStyle": primary["artStyle"],
            "music": primary["music"],
            "voice": primary["voice"],
        }

    py_bin = str(PY_WRAPPER if PY_WRAPPER.exists() else sys.executable)
    res = subprocess.run(
        [py_bin, str(SKILL_DIR / "scripts" / "studio.py"), "recommend", "--topic", prompt or "bizarre true story", "--json"],
        capture_output=True, text=True,
    )
    if res.returncode == 0 and res.stdout.strip():
        try:
            rec = json.loads(res.stdout)
            fmt = rec.get("recommended_format", "stick-story")
            art = rec.get("recommended_art_style", "default")
            music = "tension" if fmt == "night-file" else "bed" if fmt in {"deep-dive", "paper-atlas", "inside-out"} else "bounce"
            return {"format": fmt, "artStyle": art, "music": music, "voice": "am_michael"}
        except Exception:
            pass
    return {"format": "stick-story", "artStyle": "default", "music": "bounce", "voice": "am_michael"}


def seed_draft_from_prompt(proj: Path, prompt: str, filter_ids: list[str], cfg: dict, voice: str, duration: str) -> None:
    """Update scaffolded script.json & metadata.json with non-cliché draft hooks & genre tags."""
    sp = proj / "script.json"
    script = read_json(sp, {})
    clean_topic = " ".join(prompt.split()).strip() or proj.name.replace("-", " ").title()
    title = clean_topic[:56].rstrip(".,!? ")
    if len(title) >= 4 and title[0].islower():
        title = title[0].upper() + title[1:]

    tags_extra = []
    for fid in filter_ids:
        tags_extra.extend(FILTER_MAP.get(fid, {}).get("hashtags", []))
    if not tags_extra:
        tags_extra = ["#history", "#truestory"]

    chosen_voice = voice or cfg["voice"]
    script["title"] = title
    script["format"] = cfg["format"]
    script["artStyle"] = cfg["artStyle"]
    script["durationTier"] = duration or "standard"
    script["voice"] = chosen_voice
    if "vo" in script:
        script["vo"] = chosen_voice
    script["music"] = cfg["music"]
    script["genreTags"] = list(filter_ids)
    script["userPrompt"] = clean_topic
    script["hooks"] = [
        f"Most people have never heard the real story behind {clean_topic}.",
        f"One unexpected detail changed everything about {clean_topic}.",
        f"Here is what actually happened with {clean_topic}.",
    ]
    sp.write_text(json.dumps(script, indent=2) + "\n")

    # Initialize clean metadata preview with genre hashtags
    subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / "studio.py"), "metadata", str(proj)], capture_output=True)
    mp = proj / "metadata.json"
    meta = read_json(mp, {})
    yt = meta.get("youtube_shorts", {})
    if yt:
        base_desc = yt.get("description", "")
        hash_line = " ".join(dict.fromkeys(["#shorts", *tags_extra, "#33SN0W"]))
        if "\n\n#" in base_desc:
            base_desc = base_desc.rsplit("\n\n#", 1)[0]
        yt["description"] = f"{base_desc.strip()}\n\n{hash_line}".strip()
        mp.write_text(json.dumps(meta, indent=2) + "\n")


def create_batch_drafts(projects_dir: Path, payload: dict) -> list[dict]:
    prompt = str(payload.get("prompt") or "").strip()
    filter_ids = [f for f in (payload.get("filters") or []) if f in FILTER_MAP]
    look = str(payload.get("look") or "auto").strip()
    voice = str(payload.get("voice") or "").strip()
    duration = str(payload.get("duration") or "standard").strip()
    if duration not in {"short", "standard", "extended"}:
        duration = "standard"
    count = max(1, min(6, int(payload.get("count") or 1)))

    # Gather topic seed(s)
    seeds: list[str] = []
    if prompt:
        seeds.append(prompt)
    for fid in filter_ids:
        for smp in FILTER_MAP[fid]["samples"]:
            if len(seeds) < count and smp not in seeds:
                seeds.append(smp)
    idx_extra = 1
    while len(seeds) < count:
        base = prompt or (FILTER_MAP[filter_ids[0]]["label"] if filter_ids else "Untold True Story")
        seeds.append(f"{base} (Part {idx_extra + 1})")
        idx_extra += 1

    created = []
    for topic in seeds[:count]:
        cfg = choose_direction(topic, filter_ids, look)
        base_slug = slugify(topic)
        slug = base_slug
        n = 2
        while (projects_dir / slug).exists():
            slug = f"{base_slug}-{n}"
            n += 1
        cmd = [
            "bash", str(SKILL_DIR / "scripts" / "new_video.sh"),
            cfg["format"], slug,
            "--art-style", cfg["artStyle"],
            "--duration", duration,
            "--title", topic[:58],
            "--dir", str(projects_dir),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError((res.stderr or res.stdout).strip())
        proj = projects_dir / slug
        seed_draft_from_prompt(proj, topic, filter_ids, cfg, voice, duration)
        created.append(summarize_project(proj))
    return created


def build_job_steps(action: str, proj: Path, payload: dict) -> list[tuple[str, list[str], Path]]:
    py_bin = str(PY_WRAPPER if PY_WRAPPER.exists() else sys.executable)
    mp4_name = f"renders/{proj.name}.mp4"
    art = str(payload.get("artStyle") or "").strip()
    art_args = ["--art-style", art] if art and art != "default" else []

    if action == "render_all":
        return [
            ("Voice narration", [py_bin, str(SKILL_DIR / "scripts" / "voice.py"), "."], proj),
            ("Word timing", [py_bin, str(SKILL_DIR / "scripts" / "words.py"), "."], proj),
            ("Audio cues", ["node", "tools/capture.mjs", "cues"], proj),
            ("Audio mix", [py_bin, "tools/mix.py", "."], proj),
            ("Render video", ["node", "tools/capture.mjs", "video", mp4_name, "--fps", "30", *art_args], proj),
            ("Storyboard frames", ["node", "tools/capture.mjs", "sheet", "review/all.jpg", "2", "--safe-zones", *art_args], proj),
            ("Metadata", [sys.executable, str(SKILL_DIR / "scripts" / "studio.py"), "metadata", "."], proj),
            ("Quality check", [py_bin, str(SKILL_DIR / "scripts" / "qa_check.py"), "."], proj),
            ("Log analytics", [sys.executable, str(SKILL_DIR / "scripts" / "analytics.py"), "log-video", "."], proj),
        ]
    if action == "preview_frames":
        return [
            ("Scene check", ["node", "tools/capture.mjs", "check", *art_args], proj),
            ("Audio cues", ["node", "tools/capture.mjs", "cues"], proj),
            ("Storyboard frames", ["node", "tools/capture.mjs", "sheet", "review/all.jpg", "2", "--safe-zones", *art_args], proj),
        ]
    if action == "voice_words":
        return [
            ("Voice narration", [py_bin, str(SKILL_DIR / "scripts" / "voice.py"), "."], proj),
            ("Word timing", [py_bin, str(SKILL_DIR / "scripts" / "words.py"), "."], proj),
        ]
    raise ValueError(f"Unsupported action: {action!r}")


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>33SN0W Studio</title>
  <style>
    :root {
      --bg: #000000;
      --bg-glow: radial-gradient(circle at 50% -10%, #1c1c1e 0%, #000000 58%);
      --glass: rgba(24, 24, 27, 0.78);
      --surface-1: #111113;
      --surface-2: #1c1c1e;
      --surface-3: #2c2c2e;
      --hairline: rgba(255, 255, 255, 0.09);
      --hairline-strong: rgba(255, 255, 255, 0.16);
      --text: #f5f5f7;
      --text-2: #a1a1a6;
      --text-3: #6e6e73;
      --blue: #0a84ff;
      --blue-hover: #2d95ff;
      --green: #30d158;
      --amber: #ff9f0a;
      --red: #ff453a;
      --radius-lg: 20px;
      --radius-md: 14px;
      --radius-sm: 10px;
      --ease: cubic-bezier(0.22, 1, 0.36, 1);
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      min-height: 100%;
      background: var(--bg);
      background-image: var(--bg-glow);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif;
      font-size: 14px;
      line-height: 1.48;
      -webkit-font-smoothing: antialiased;
    }

    /* Sticky frosted Apple toolbar */
    .topbar {
      position: sticky;
      top: 0;
      z-index: 40;
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 16px;
      padding: 12px 24px;
      background: var(--glass);
      backdrop-filter: blur(26px) saturate(180%);
      -webkit-backdrop-filter: blur(26px) saturate(180%);
      border-bottom: 1px solid var(--hairline);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 600;
      font-size: 15px;
      letter-spacing: -0.015em;
    }
    .brand-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: linear-gradient(135deg, #f5f5f7, #8e8e93);
      box-shadow: 0 0 12px rgba(255,255,255,0.28);
    }
    .segmented {
      display: inline-flex;
      background: var(--surface-2);
      border: 1px solid var(--hairline);
      border-radius: 999px;
      padding: 3px;
      gap: 2px;
    }
    .seg-btn {
      appearance: none;
      border: 0;
      background: transparent;
      color: var(--text-2);
      padding: 6px 18px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 180ms var(--ease);
    }
    .seg-btn.active {
      background: var(--surface-3);
      color: var(--text);
      box-shadow: 0 2px 8px rgba(0,0,0,0.45);
    }
    .top-right {
      display: flex;
      justify-content: flex-end;
      align-items: center;
      gap: 10px;
    }

    /* Buttons */
    .btn {
      appearance: none;
      border: 1px solid var(--hairline-strong);
      background: var(--surface-2);
      color: var(--text);
      padding: 8px 16px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 160ms var(--ease);
      display: inline-flex;
      align-items: center;
      gap: 7px;
      white-space: nowrap;
    }
    .btn:hover { background: var(--surface-3); transform: translateY(-0.5px); }
    .btn:active { transform: translateY(0); }
    .btn:disabled { opacity: 0.42; cursor: not-allowed; transform: none; }
    .btn.primary { background: var(--blue); border-color: transparent; color: #fff; }
    .btn.primary:hover { background: var(--blue-hover); }
    .btn.ready { background: var(--green); border-color: transparent; color: #051b0c; font-weight: 700; }
    .btn.ready:hover { filter: brightness(1.06); }
    .btn.quiet { background: transparent; border-color: var(--hairline); color: var(--text-2); }
    .btn.quiet:hover { color: var(--text); background: rgba(255,255,255,0.06); }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 3px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 600;
      white-space: nowrap;
      flex-shrink: 0;
      background: var(--surface-2);
      color: var(--text-2);
      border: 1px solid var(--hairline);
    }
    .badge.ok { color: var(--green); border-color: rgba(48,209,88,0.3); background: rgba(48,209,88,0.1); }
    .badge.warn { color: var(--amber); border-color: rgba(255,159,10,0.3); background: rgba(255,159,10,0.1); }
    .badge.live { color: var(--blue); border-color: rgba(10,132,255,0.35); background: rgba(10,132,255,0.12); }

    .container { max-width: 1240px; margin: 0 auto; padding: 26px 24px 64px; }
    .card {
      background: var(--surface-1);
      border: 1px solid var(--hairline);
      border-radius: var(--radius-lg);
      padding: 22px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45);
    }
    .card-subtle {
      background: var(--surface-2);
      border: 1px solid var(--hairline);
      border-radius: var(--radius-md);
      padding: 16px;
    }
    h2 { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.025em; }
    h3 { margin: 0 0 12px; font-size: 16px; font-weight: 600; letter-spacing: -0.015em; }
    .subtitle { margin: 6px 0 0; color: var(--text-2); font-size: 14px; }

    /* Inputs & Filter Chips */
    textarea.prompt-box {
      width: 100%;
      min-height: 92px;
      background: var(--surface-2);
      border: 1px solid var(--hairline-strong);
      border-radius: var(--radius-md);
      color: var(--text);
      padding: 14px 16px;
      font-family: inherit;
      font-size: 16px;
      line-height: 1.45;
      resize: vertical;
      outline: none;
      transition: border-color 160ms var(--ease);
    }
    textarea.prompt-box:focus { border-color: var(--blue); }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; }
    .chip {
      border: 1px solid var(--hairline-strong);
      background: var(--surface-2);
      color: var(--text-2);
      padding: 8px 15px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 160ms var(--ease);
    }
    .chip:hover { color: var(--text); background: var(--surface-3); }
    .chip.selected {
      background: var(--text);
      color: #000;
      border-color: var(--text);
    }
    select, input[type="text"], input[type="datetime-local"] {
      width: 100%;
      background: var(--surface-2);
      border: 1px solid var(--hairline);
      border-radius: var(--radius-sm);
      color: var(--text);
      padding: 9px 12px;
      font-family: inherit;
      font-size: 13.5px;
      outline: none;
    }
    select:focus, input[type="text"]:focus { border-color: var(--blue); }
    label.lbl {
      display: block;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-2);
      margin-bottom: 6px;
      letter-spacing: 0.01em;
    }

    /* Count Selector Pills */
    .count-pills { display: inline-flex; gap: 6px; background: var(--surface-2); padding: 4px; border-radius: 12px; border: 1px solid var(--hairline); }
    .cnt-btn {
      border: 0; background: transparent; color: var(--text-2);
      min-width: 40px; height: 32px; padding: 0 12px; border-radius: 8px;
      font-size: 13px; font-weight: 600; cursor: pointer;
    }
    .cnt-btn.active { background: var(--surface-3); color: var(--text); }

    /* Review Workspace */
    .review-layout { display: grid; grid-template-columns: 290px 1fr; gap: 20px; align-items: start; }
    .library-list { display: flex; flex-direction: column; gap: 8px; max-height: 70vh; overflow-y: auto; margin-top: 12px; }
    .lib-item {
      width: 100%;
      text-align: left;
      background: var(--surface-2);
      border: 1px solid transparent;
      border-radius: var(--radius-md);
      padding: 12px 14px;
      cursor: pointer;
      color: var(--text);
      transition: all 150ms var(--ease);
    }
    .lib-item:hover { background: var(--surface-3); }
    .lib-item.active { border-color: var(--blue); background: rgba(10,132,255,0.12); }
    .lib-title { font-weight: 600; font-size: 13.5px; margin-bottom: 4px; }
    .lib-meta { font-size: 12px; color: var(--text-2); display: flex; justify-content: space-between; align-items: center; }

    .review-hero { display: grid; grid-template-columns: 310px 1fr; gap: 22px; align-items: start; }
    .phone-frame {
      background: #050506;
      border: 1px solid var(--hairline-strong);
      border-radius: 26px;
      padding: 10px;
      box-shadow: 0 24px 48px rgba(0,0,0,0.65);
    }
    .phone-frame video {
      width: 100%;
      aspect-ratio: 9 / 16;
      border-radius: 18px;
      display: block;
      background: #000;
    }
    .phone-empty {
      width: 100%;
      aspect-ratio: 9 / 16;
      border-radius: 18px;
      background: var(--surface-2);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 20px;
      color: var(--text-2);
      gap: 12px;
    }

    .hook-option {
      display: flex;
      gap: 10px;
      align-items: center;
      background: var(--surface-2);
      border: 1px solid var(--hairline);
      border-radius: var(--radius-sm);
      padding: 10px 12px;
      margin-bottom: 8px;
    }
    .scene-line {
      background: var(--surface-2);
      border: 1px solid var(--hairline);
      border-radius: var(--radius-md);
      padding: 12px 14px;
      margin-bottom: 10px;
    }
    .scene-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 12px; color: var(--text-2); font-weight: 600; }
    .sheet-thumb {
      width: 100%;
      border-radius: var(--radius-md);
      border: 1px solid var(--hairline);
      cursor: zoom-in;
      display: block;
    }
    .sheet-thumb.zoomed {
      position: fixed; inset: 24px; width: calc(100vw - 48px); height: calc(100vh - 48px);
      object-fit: contain; background: rgba(0,0,0,0.92); z-index: 80; cursor: zoom-out; border-radius: 16px;
    }

    /* Batch Upload Cards */
    .upload-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; margin: 16px 0; }
    .upload-card {
      background: var(--surface-2);
      border: 1px solid var(--hairline);
      border-radius: var(--radius-md);
      padding: 14px;
      cursor: pointer;
      transition: all 160ms var(--ease);
    }
    .upload-card.picked { border-color: var(--blue); background: rgba(10,132,255,0.1); }
    .status-strip {
      position: fixed;
      bottom: 18px;
      right: 24px;
      z-index: 50;
      width: min(410px, calc(100vw - 32px));
      background: rgba(28, 28, 30, 0.9);
      backdrop-filter: blur(22px);
      border: 1px solid var(--hairline-strong);
      border-radius: 16px;
      padding: 14px 16px;
      box-shadow: 0 20px 44px rgba(0,0,0,0.7);
      display: none;
    }
    @media (max-width: 960px) {
      .topbar { grid-template-columns: 1fr; justify-items: center; }
      .review-layout, .review-hero { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>

<header class="topbar">
  <div class="brand">
    <span class="brand-dot"></span>
    <span>33SN0W Studio</span>
  </div>
  <nav class="segmented">
    <button class="seg-btn active" data-view="create">Create</button>
    <button class="seg-btn" data-view="review">Review</button>
    <button class="seg-btn" data-view="upload">Upload</button>
  </nav>
  <div class="top-right">
    <span id="ytChannelPill" class="badge">YouTube Checking…</span>
  </div>
</header>

<div class="container">

  <!-- VIEW 1: CREATE (Prompt + Category Filters + Video Count) -->
  <section id="view-create">
    <div class="card" style="max-width:920px;margin:0 auto;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;">
        <div>
          <h2>What kind of video are you thinking of?</h2>
          <p class="subtitle">Describe your idea, pick one or more categories, and choose how many Shorts drafts to spin up.</p>
        </div>
        <span class="badge ok">Runs 100% locally · $0</span>
      </div>

      <div style="margin-top:20px;">
        <label class="lbl">Your Video Idea or Prompt</label>
        <textarea id="createPrompt" class="prompt-box" placeholder="e.g. A strange true story from the 1800s about a town that fought over a stray pig, or a creepy ocean mystery…"></textarea>
      </div>

      <div style="margin-top:18px;">
        <label class="lbl">Video Style &amp; Genre Filters</label>
        <div id="filterChips" class="chips"></div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(2,minmax(240px,1fr));gap:16px;margin-top:20px;">
        <div>
          <label class="lbl">How many videos to create?</label>
          <div id="createCountPills" class="count-pills">
            <button type="button" class="cnt-btn active" data-cnt="1">1</button>
            <button type="button" class="cnt-btn" data-cnt="2">2</button>
            <button type="button" class="cnt-btn" data-cnt="3">3</button>
            <button type="button" class="cnt-btn" data-cnt="4">4</button>
            <button type="button" class="cnt-btn" data-cnt="5">5</button>
          </div>
        </div>
        <div>
          <label class="lbl">Visual Look</label>
          <select id="createLook"></select>
        </div>
        <div>
          <label class="lbl">Narrator Voice</label>
          <select id="createVoice"></select>
        </div>
        <div>
          <label class="lbl">Length</label>
          <select id="createDuration">
            <option value="short">Short (20–30 sec)</option>
            <option value="standard" selected>Standard (35–45 sec)</option>
            <option value="extended">Extended (45–60 sec)</option>
          </select>
        </div>
      </div>

      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:24px;padding-top:18px;border-top:1px solid var(--hairline);flex-wrap:wrap;gap:12px;">
        <div style="color:var(--text-2);font-size:13px;" id="createSummary">Creates 1 customizable draft and opens it for voice &amp; story review.</div>
        <button class="btn primary" id="createSubmitBtn" style="padding:11px 24px;font-size:14px;">Create Video Draft</button>
      </div>
    </div>
  </section>

  <!-- VIEW 2: REVIEW (Human-friendly video + story + frames review) -->
  <section id="view-review" style="display:none;">
    <div class="review-layout">
      <div class="card" style="padding:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
          <h3 style="margin:0;">Your Videos</h3>
          <span id="libCount" class="badge">0</span>
        </div>
        <input type="text" id="libSearch" placeholder="Filter by title or theme…" />
        <div style="display:flex;gap:6px;margin-top:8px;">
          <button class="cnt-btn active" data-lfilter="all" style="font-size:12px;height:28px;">All</button>
          <button class="cnt-btn" data-lfilter="ready" style="font-size:12px;height:28px;">Ready</button>
          <button class="cnt-btn" data-lfilter="uploaded" style="font-size:12px;height:28px;">Uploaded</button>
        </div>
        <div id="libList" class="library-list"></div>
      </div>

      <div id="reviewMain" style="display:none;">
        <div class="card" style="margin-bottom:18px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex-wrap:wrap;">
            <div>
              <h2 id="rvHeading" style="font-size:22px;">—</h2>
              <p class="subtitle" id="rvSubheading">—</p>
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
              <button class="btn quiet" id="btnPreviewFrames">Preview Frames</button>
              <button class="btn" id="btnRenderVideo">Render Video</button>
              <button class="btn ready" id="btnOneClickUpload">Upload to YouTube</button>
            </div>
          </div>

          <div id="rvReadinessRow" style="display:flex;flex-wrap:wrap;gap:8px;margin-top:14px;"></div>
        </div>

        <div class="review-hero">
          <!-- Left: Watchable Phone Preview -->
          <div class="phone-frame">
            <div id="phoneMedia"></div>
          </div>

          <!-- Right: Normal Creator-Friendly Story & Voice Editor -->
          <div style="display:flex;flex-direction:column;gap:16px;">
            <div class="card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <h3 style="margin:0;">Voice &amp; Title</h3>
                <button class="btn quiet" id="rvSaveBtn" style="padding:6px 14px;">Save Story Edits</button>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
                <div style="grid-column:span 2;">
                  <label class="lbl">Video Title</label>
                  <input type="text" id="rvTitle" />
                </div>
                <div>
                  <label class="lbl">Voice</label>
                  <select id="rvVoice"></select>
                </div>
                <div>
                  <label class="lbl">Background Feel</label>
                  <select id="rvMusic">
                    <option value="bounce">Upbeat Storytelling</option>
                    <option value="bed">Calm Documentary</option>
                    <option value="tension">Suspense / Mystery</option>
                    <option value="none">Voice Only</option>
                  </select>
                </div>
              </div>
              <div style="display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap;">
                <button class="btn" id="rvHearHookBtn">Hear Opening Voice</button>
                <button class="btn quiet" id="rvHearFullBtn">Play Saved Narration</button>
                <audio id="rvAudio" controls style="height:32px;flex:1;min-width:180px;"></audio>
              </div>
            </div>

            <div class="card">
              <h3>Opening Hook Options</h3>
              <p class="subtitle" style="margin:-6px 0 12px;font-size:12.5px;">Click <strong>Use</strong> on the opener that grabs attention fastest.</p>
              <div id="rvHooksBox"></div>
            </div>

            <div class="card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <h3 style="margin:0;">Story Scenes (<span id="rvSceneCount">0</span>)</h3>
                <button class="btn quiet" id="rvAddSceneBtn" style="padding:5px 12px;">+ Add Scene</button>
              </div>
              <div id="rvScenesBox"></div>
            </div>

            <div class="card">
              <h3>Visual Storyboard Preview</h3>
              <p class="subtitle" style="margin:-6px 0 12px;font-size:12.5px;">Click to enlarge and confirm characters and captions fit inside the mobile frame.</p>
              <div id="rvSheetBox" style="color:var(--text-2);">No frame preview generated yet.</div>
            </div>

            <div class="card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <h3 style="margin:0;">Fact Sources &amp; Caption Preview</h3>
                <span id="rvVerifyBadge" class="badge">Checking…</span>
              </div>
              <div id="rvMetaDesc" style="color:var(--text-2);font-size:13px;white-space:pre-wrap;background:var(--surface-2);padding:12px;border-radius:10px;border:1px solid var(--hairline);">—</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- VIEW 3: BATCH UPLOAD -->
  <section id="view-upload" style="display:none;">
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex-wrap:wrap;">
        <div>
          <h2>Upload to YouTube</h2>
          <p class="subtitle">Choose how many videos to upload, confirm the selection below, and publish privately in one click.</p>
        </div>
        <div style="display:flex;gap:8px;align-items:center;" id="upOAuthStatus"></div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:20px;padding:16px;background:var(--surface-2);border-radius:var(--radius-md);border:1px solid var(--hairline);">
        <div>
          <label class="lbl">Number of videos to upload</label>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <div id="upCountPills" class="count-pills">
              <button type="button" class="cnt-btn active" data-ucnt="1">1</button>
              <button type="button" class="cnt-btn" data-ucnt="2">2</button>
              <button type="button" class="cnt-btn" data-ucnt="3">3</button>
              <button type="button" class="cnt-btn" data-ucnt="5">5</button>
              <button type="button" class="cnt-btn" data-ucnt="all">All</button>
            </div>
            <input type="number" id="upCustomCount" min="1" max="50" value="1" title="Custom count" style="width:66px;text-align:center;background:var(--surface-1);border:1px solid var(--hairline);border-radius:10px;color:var(--text);padding:7px 8px;font-size:13px;" />
          </div>
        </div>
        <div>
          <label class="lbl">Release timing</label>
          <select id="upScheduleMode">
            <option value="now">Upload right now (Private in Studio)</option>
            <option value="stagger">Schedule daily automatically (24h apart)</option>
          </select>
        </div>
        <div id="upStartWrap" style="display:none;">
          <label class="lbl">First video publish time (UTC, optional)</label>
          <input type="text" id="upStartAt" placeholder="e.g. 2026-11-13T18:00:00Z" />
        </div>
      </div>

      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:18px;">
        <span class="subtitle" id="upSelectionHint" style="margin:0;">Select videos below</span>
        <button class="btn ready" id="upRunBatchBtn" style="padding:11px 24px;font-size:14px;">Upload Selected Videos</button>
      </div>

      <div id="upCardsGrid" class="upload-grid"></div>
    </div>
  </section>

</div>

<!-- Non-intrusive floating progress pill -->
<div id="statusToast" class="status-strip">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
    <strong id="toastTitle" style="font-size:13.5px;">Working…</strong>
    <span id="toastBadge" class="badge live">Running</span>
  </div>
  <div id="toastDetail" style="font-size:12px;color:var(--text-2);margin-top:6px;max-height:76px;overflow-y:auto;white-space:pre-line;">Preparing…</div>
</div>

<script>
const $ = (id) => document.getElementById(id);

const app = {
  view: "create",
  projects: [],
  activeSlug: null,
  detail: null,
  filters: [],
  looks: [],
  voices: [],
  selectedFilters: new Set(["history"]),
  createCount: 1,
  libFilter: "all",
  uploadPickCount: 1,
  pickedSlugs: new Set(),
  pollTimer: null,
};

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));

async function api(url, opts = {}) {
  const res = await fetch(url, opts);
  const ctype = res.headers.get("content-type") || "";
  if (ctype.includes("application/json")) {
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res;
}

function switchView(v) {
  app.view = v;
  document.querySelectorAll(".seg-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === v));
  ["create", "review", "upload"].forEach((k) => {
    $(`view-${k}`).style.display = k === v ? "block" : "none";
  });
  if (v === "upload") renderUploadCards();
}

async function init() {
  const [meta, vdata] = await Promise.all([api("/api/filters"), api("/api/voices")]);
  app.filters = meta.filters || [];
  app.looks = meta.looks || [];
  app.voices = vdata.voices || [];

  renderCreateControls();
  const voiceHtml = app.voices.map(([id, label]) => `<option value="${esc(id)}">${esc(label)}</option>`).join("");
  $("createVoice").innerHTML = `<option value="">Smart Match for Genre</option>` + voiceHtml;
  $("rvVoice").innerHTML = voiceHtml;
  $("createLook").innerHTML = app.looks.map(([id, label]) => `<option value="${esc(id)}">${esc(label)}</option>`).join("");

  await refreshLibrary();
  updateOAuthBadge();
  const qv = new URLSearchParams(window.location.search).get("view");
  if (qv && ["create", "review", "upload"].includes(qv)) switchView(qv);
}

function renderCreateControls() {
  const box = $("filterChips");
  box.innerHTML = "";
  app.filters.forEach((f) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip" + (app.selectedFilters.has(f.id) ? " selected" : "");
    btn.textContent = f.label;
    btn.onclick = () => {
      if (app.selectedFilters.has(f.id)) app.selectedFilters.delete(f.id);
      else app.selectedFilters.add(f.id);
      renderCreateControls();
      updateCreateSummary();
    };
    box.appendChild(btn);
  });
  updateCreateSummary();
}

function updateCreateSummary() {
  const n = app.createCount;
  const genres = [...app.selectedFilters].map((id) => app.filters.find((x) => x.id === id)?.label).filter(Boolean);
  const gText = genres.length ? genres.join(" + ") : "Auto-matched theme";
  $("createSubmitBtn").textContent = n === 1 ? "Create Video Draft" : `Create ${n} Video Drafts`;
  $("createSummary").textContent = `Creates ${n} local draft${n > 1 ? "s" : ""} (${gText}) and opens Review.`;
}

async function refreshLibrary(selectSlug = null) {
  const data = await api("/api/projects");
  app.projects = data.projects || [];
  $("libCount").textContent = `${app.projects.length}`;
  renderLibrary();

  const target = selectSlug || app.activeSlug || (app.projects[0]?.slug || null);
  if (target) await loadProject(target);
  applyAutoUploadCount(app.uploadPickCount);
  if (app.view === "upload") renderUploadCards();
}

function renderLibrary() {
  const q = ($("libSearch").value || "").toLowerCase();
  const items = app.projects.filter((p) => {
    if (app.libFilter === "ready" && (p.uploaded || !p.has_mp4)) return false;
    if (app.libFilter === "uploaded" && !p.uploaded) return false;
    if (q && !`${p.title} ${p.slug} ${p.format}`.toLowerCase().includes(q)) return false;
    return true;
  });
  const list = $("libList");
  list.innerHTML = "";
  items.forEach((p) => {
    const btn = document.createElement("button");
    btn.className = "lib-item" + (p.slug === app.activeSlug ? " active" : "");
    const statusPill = p.uploaded
      ? `<span class="badge ok">On YouTube</span>`
      : p.has_mp4
        ? `<span class="badge live">Ready</span>`
        : `<span class="badge warn">Draft</span>`;
    btn.innerHTML = `<div class="lib-title">${esc(p.title)}</div><div class="lib-meta"><span>${p.line_count} scenes</span>${statusPill}</div>`;
    btn.onclick = () => loadProject(p.slug);
    list.appendChild(btn);
  });
}

async function loadProject(slug) {
  app.activeSlug = slug;
  renderLibrary();
  const d = await api(`/api/project?slug=${encodeURIComponent(slug)}`);
  app.detail = d;
  $("reviewMain").style.display = "block";

  const s = d.script || {};
  $("rvHeading").textContent = s.title || d.slug;
  $("rvSubheading").textContent = `${(s.format || "story").replace("-", " ")} · ${(s.lines || []).length} scenes` + (d.mp4_mb ? ` · ${d.mp4_mb} MB ready` : "");

  // Plain-English readiness pills
  const pills = [];
  if (d.has_mp4) pills.push(`<span class="badge ok">Video Rendered</span>`);
  else pills.push(`<span class="badge warn">Needs Render</span>`);
  if (d.audio_ok) pills.push(`<span class="badge ok">Clear Voice & Mix</span>`);
  if (d.visual_ok) pills.push(`<span class="badge ok">Framing Verified</span>`);
  if (d.sources_count > 0 && d.verified_sources) pills.push(`<span class="badge ok">${d.sources_count} Sources Checked</span>`);
  else pills.push(`<span class="badge warn">Add Source Links</span>`);
  if (d.receipt?.url) pills.push(`<a class="badge ok" style="text-decoration:none;" href="${esc(d.receipt.url)}" target="_blank">YouTube Private ↗</a>`);
  $("rvReadinessRow").innerHTML = pills.join("");

  $("btnOneClickUpload").textContent = d.receipt?.url ? "Re-Upload Video" : "Upload Video (Private)";
  $("btnOneClickUpload").disabled = !d.has_mp4;

  const ts = Date.now();
  $("phoneMedia").innerHTML = d.has_mp4
    ? `<video controls preload="metadata" src="/api/media?project=${encodeURIComponent(d.slug)}&kind=mp4&t=${ts}#t=0.8"></video>`
    : `<div class="phone-empty"><strong>Not rendered yet</strong><span style="font-size:13px;">Review your story on the right, then click <strong>Render Video</strong> to watch it here.</span></div>`;

  $("rvTitle").value = s.title || "";
  $("rvVoice").value = s.voice || s.vo || "am_michael";
  $("rvMusic").value = s.music || "bounce";

  renderHooks(s.hooks || []);
  renderScenes(s.lines || []);

  $("rvSheetBox").innerHTML = d.has_sheet
    ? `<img src="/api/media?project=${encodeURIComponent(d.slug)}&kind=sheet&t=${ts}" class="sheet-thumb" onclick="this.classList.toggle('zoomed')" />`
    : `Click <strong>Preview Frames</strong> above to see a full scene-by-scene storyboard grid.`;

  const yt = d.metadata?.youtube_shorts;
  $("rvVerifyBadge").textContent = d.verified_sources ? "Sources Verified" : "Draft";
  $("rvVerifyBadge").className = "badge " + (d.verified_sources ? "ok" : "warn");
  $("rvMetaDesc").textContent = yt ? `${yt.recommended_title}\n\n${yt.description}` : "Save & Render to generate YouTube title, sources, and hashtags.";
}

function renderHooks(hooks) {
  const box = $("rvHooksBox");
  box.innerHTML = "";
  hooks.forEach((h, i) => {
    const row = document.createElement("div");
    row.className = "hook-option";
    row.innerHTML = `<span class="badge">${i === 0 ? "Primary" : `Idea ${i + 1}`}</span><input type="text" value="${esc(h)}" style="flex:1;" /><button class="btn quiet" style="padding:5px 12px;">Use</button>`;
    const inp = row.querySelector("input");
    inp.oninput = () => { app.detail.script.hooks[i] = inp.value; };
    row.querySelector("button").onclick = () => {
      if (!app.detail.script.lines.length) app.detail.script.lines.push({ text: "", caps: "", pause: 0.3 });
      app.detail.script.lines[0].text = inp.value;
      renderScenes(app.detail.script.lines);
      auditionVoice(inp.value);
    };
    box.appendChild(row);
  });
}

function renderScenes(lines) {
  const box = $("rvScenesBox");
  $("rvSceneCount").textContent = `${lines.length}`;
  box.innerHTML = "";
  lines.forEach((ln, idx) => {
    const card = document.createElement("div");
    card.className = "scene-line";
    card.innerHTML = `
      <div class="scene-head">
        <span>Scene ${idx + 1}</span>
        <button class="btn quiet" style="padding:2px 9px;font-size:12px;">Remove</button>
      </div>
      <textarea style="width:100%;min-height:48px;background:var(--surface-1);border:1px solid var(--hairline);border-radius:8px;color:var(--text);padding:8px 10px;font-family:inherit;font-size:13.5px;">${esc(ln.text || "")}</textarea>
      <div style="margin-top:7px;">
        <input type="text" value="${esc((ln.caps || "").replace(/[*|]/g, " ").replace(/\s+/g, " ").trim())}" placeholder="On-screen highlight text (optional)" style="font-size:12px;padding:6px 10px;background:var(--surface-1);" />
      </div>`;
    const ta = card.querySelector("textarea");
    const capInp = card.querySelector("input");
    ta.oninput = () => { ln.text = ta.value; };
    capInp.oninput = () => { ln.caps = capInp.value; };
    card.querySelector("button").onclick = () => { lines.splice(idx, 1); renderScenes(lines); };
    box.appendChild(card);
  });
}

async function saveCurrentStory() {
  if (!app.activeSlug || !app.detail?.script) return;
  const s = app.detail.script;
  s.title = $("rvTitle").value.trim();
  s.voice = $("rvVoice").value;
  if ("vo" in s) s.vo = s.voice;
  s.music = $("rvMusic").value;
  await api("/api/project/script", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug: app.activeSlug, script: s }),
  });
  showToast("Story Saved", "Updated scenes & narrator settings.", "ok", 2200);
  await refreshLibrary(app.activeSlug);
}

async function auditionVoice(text) {
  const line = String(text || app.detail?.script?.lines?.[0]?.text || "").trim();
  if (!line) return;
  $("rvHearHookBtn").disabled = true;
  $("rvHearHookBtn").textContent = "Generating voice…";
  try {
    const res = await fetch("/api/voice/audition", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: line, voice: $("rvVoice").value, speed: 1.0 }),
    });
    if (!res.ok) throw new Error((await res.json()).error || "Voice preview unavailable");
    const blob = await res.blob();
    $("rvAudio").src = URL.createObjectURL(blob);
    await $("rvAudio").play();
  } catch (e) {
    alert(e.message);
  } finally {
    $("rvHearHookBtn").disabled = false;
    $("rvHearHookBtn").textContent = "Hear Opening Voice";
  }
}

async function runProjectJob(action, titleLabel) {
  if (!app.activeSlug) return;
  await saveCurrentStory();
  const job = await api("/api/jobs/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug: app.activeSlug, action, artStyle: app.detail?.script?.artStyle }),
  });
  watchJob(job.id, titleLabel);
}

function applyAutoUploadCount(cntVal) {
  app.uploadPickCount = cntVal;
  app.pickedSlugs.clear();
  const ready = app.projects.filter((p) => p.has_mp4 && !p.uploaded);
  const pool = ready.length ? ready : app.projects.filter((p) => p.has_mp4);
  const limit = cntVal === "all" ? pool.length : Math.min(pool.length, Number(cntVal) || 1);
  pool.slice(0, limit).forEach((p) => app.pickedSlugs.add(p.slug));
}

function renderUploadCards() {
  const grid = $("upCardsGrid");
  grid.innerHTML = "";
  const eligible = app.projects.filter((p) => p.has_mp4);
  $("upSelectionHint").textContent = `${app.pickedSlugs.size} video(s) selected for upload`;
  $("upRunBatchBtn").disabled = app.pickedSlugs.size === 0;
  $("upRunBatchBtn").textContent = app.pickedSlugs.size <= 1 ? "Upload 1 Video (Private)" : `Upload ${app.pickedSlugs.size} Videos (Private)`;

  eligible.forEach((p) => {
    const picked = app.pickedSlugs.has(p.slug);
    const card = document.createElement("div");
    card.className = "upload-card" + (picked ? " picked" : "");
    card.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;">
        <strong style="font-size:14px;">${esc(p.title)}</strong>
        <span class="badge ${p.uploaded ? "ok" : picked ? "live" : ""}">${p.uploaded ? "Already on YT" : picked ? "Selected" : "Click to pick"}</span>
      </div>
      <div style="font-size:12px;color:var(--text-2);">${p.mp4_mb || "?"} MB · ${(p.format || "").replace("-", " ")}${p.youtube_url ? ` · <a href="${esc(p.youtube_url)}" target="_blank" style="color:var(--green);" onclick="event.stopPropagation()">View Short ↗</a>` : ""}</div>`;
    card.onclick = () => {
      if (app.pickedSlugs.has(p.slug)) app.pickedSlugs.delete(p.slug);
      else app.pickedSlugs.add(p.slug);
      renderUploadCards();
    };
    grid.appendChild(card);
  });
}

async function updateOAuthBadge() {
  try {
    const first = app.projects.find((p) => p.has_mp4);
    const dry = first ? await api(`/api/upload/dry-run?slug=${encodeURIComponent(first.slug)}`) : null;
    const ready = dry ? (dry.client_secrets_present && dry.token_present) : false;
    $("ytChannelPill").textContent = ready ? "YouTube Connected" : "YouTube Auth Needed";
    $("ytChannelPill").className = "badge " + (ready ? "ok" : "warn");
    $("upOAuthStatus").innerHTML = ready
      ? `<span class="badge ok">OAuth Ready</span>`
      : `<span class="badge warn">Run --auth-only once</span>`;
  } catch {
    $("ytChannelPill").textContent = "Local Studio";
  }
}

function showToast(title, detail, stateCls = "live", autoHideMs = 0) {
  $("statusToast").style.display = "block";
  $("toastTitle").textContent = title;
  $("toastDetail").textContent = detail;
  $("toastBadge").className = `badge ${stateCls}`;
  $("toastBadge").textContent = stateCls === "ok" ? "Done" : stateCls === "warn" ? "Check" : "Running";
  if (autoHideMs > 0) setTimeout(() => { $("statusToast").style.display = "none"; }, autoHideMs);
}

function watchJob(jobId, label) {
  showToast(label, "Working in background…", "live");
  if (app.pollTimer) clearInterval(app.pollTimer);
  app.pollTimer = setInterval(async () => {
    const data = await api("/api/jobs");
    const job = (data.jobs || []).find((j) => j.id === jobId);
    if (!job) return;
    const tail = (job.log || []).slice(-4).join("\n") || "Running…";
    if (job.status === "running") {
      showToast(label, tail, "live");
      return;
    }
    clearInterval(app.pollTimer);
    app.pollTimer = null;
    if (job.status === "completed") {
      showToast(`${label} Complete`, tail, "ok", 5000);
      await refreshLibrary(app.activeSlug);
      if (app.view === "upload") renderUploadCards();
    } else {
      showToast(`${label} Stopped`, tail, "warn", 7000);
    }
  }, 1300);
}

// Navigation & Events
document.querySelectorAll(".seg-btn").forEach((b) => { b.onclick = () => switchView(b.dataset.view); });
document.querySelectorAll("[data-cnt]").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll("[data-cnt]").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    app.createCount = Number(b.dataset.cnt);
    updateCreateSummary();
  };
});
document.querySelectorAll("[data-lfilter]").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll("[data-lfilter]").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    app.libFilter = b.dataset.lfilter;
    renderLibrary();
  };
});
document.querySelectorAll("[data-ucnt]").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll("[data-ucnt]").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    applyAutoUploadCount(b.dataset.ucnt);
    if (b.dataset.ucnt !== "all") $("upCustomCount").value = b.dataset.ucnt;
    renderUploadCards();
  };
});
$("upCustomCount").oninput = () => {
  const v = Math.max(1, Number($("upCustomCount").value || 1));
  document.querySelectorAll("[data-ucnt]").forEach((x) => x.classList.toggle("active", x.dataset.ucnt === String(v)));
  applyAutoUploadCount(v);
  renderUploadCards();
};

$("libSearch").oninput = renderLibrary;
$("upScheduleMode").onchange = () => {
  $("upStartWrap").style.display = $("upScheduleMode").value === "stagger" ? "block" : "none";
};

$("createSubmitBtn").onclick = async () => {
  const prompt = $("createPrompt").value.trim();
  if (!prompt && app.selectedFilters.size === 0) return alert("Describe your idea or pick a category filter first.");
  $("createSubmitBtn").disabled = true;
  $("createSubmitBtn").textContent = "Creating Drafts…";
  try {
    const res = await api("/api/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        filters: [...app.selectedFilters],
        look: $("createLook").value,
        voice: $("createVoice").value,
        duration: $("createDuration").value,
        count: app.createCount,
      }),
    });
    const firstSlug = res.created?.[0]?.slug;
    await refreshLibrary(firstSlug);
    switchView("review");
    showToast("Draft Ready", `Created ${res.created.length} draft(s). Edit scenes or click Render Video.`, "ok", 4500);
  } catch (e) {
    alert(e.message);
  } finally {
    $("createSubmitBtn").disabled = false;
    updateCreateSummary();
  }
};

$("rvSaveBtn").onclick = saveCurrentStory;
$("rvHearHookBtn").onclick = () => auditionVoice(app.detail?.script?.lines?.[0]?.text);
$("rvHearFullBtn").onclick = () => {
  if (!app.activeSlug) return;
  $("rvAudio").src = `/api/media?project=${encodeURIComponent(app.activeSlug)}&kind=narration&t=${Date.now()}`;
  $("rvAudio").play().catch(() => alert("Render the video voice first, or click Hear Opening Voice."));
};
$("rvAddSceneBtn").onclick = () => {
  app.detail.script.lines.push({ text: "", caps: "", pause: 0.3 });
  renderScenes(app.detail.script.lines);
};

$("btnPreviewFrames").onclick = () => runProjectJob("preview_frames", "Preview Frames");
$("btnRenderVideo").onclick = () => runProjectJob("render_all", "Rendering Video");

$("btnOneClickUpload").onclick = async () => {
  if (!app.activeSlug) return;
  const already = !!app.detail?.receipt?.url;
  const job = await api("/api/upload/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slugs: [app.activeSlug], privacy: "private", force: already }),
  });
  watchJob(job.id, "Uploading Video");
};

$("upRunBatchBtn").onclick = async () => {
  const slugs = [...app.pickedSlugs];
  if (!slugs.length) return;
  const stagger = $("upScheduleMode").value === "stagger";
  const pubAt = stagger ? ($("upStartAt").value.trim() || new Date(Date.now() + 3600 * 1000).toISOString().replace(/\.\d+Z$/, "Z")) : "";
  const force = slugs.some((s) => app.projects.find((p) => p.slug === s)?.uploaded);
  const job = await api("/api/upload/batch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slugs, privacy: "private", publish_at: pubAt, stagger_hours: 24, force }),
  });
  watchJob(job.id, `Uploading ${slugs.length} Video(s)`);
};

init().catch((e) => showToast("Setup Note", e.message, "warn"));
</script>
</body>
</html>
"""


def make_handler(projects_dir: Path, jobs: JobManager):
    class StudioHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _send_json(self, code: int, payload: dict) -> None:
            raw = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read_json_body(self) -> dict:
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length > 2_000_000:
                raise ValueError("Request too large")
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")

        def _serve_file_range(self, path: Path, content_type: str) -> None:
            if not path.is_file():
                self._send_json(404, {"error": f"File not ready yet: {path.name}"})
                return
            size = path.stat().st_size
            rng = self.headers.get("Range")
            start, end, status = 0, size - 1, 200
            if rng and rng.startswith("bytes="):
                spec = rng[6:].split(",")[0].strip()
                a, b = spec.split("-", 1)
                start = int(a) if a else max(0, size - int(b))
                end = min(int(b) if a and b else size - 1, size - 1)
                if start > end or start < 0:
                    self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                status = 206

            length = end - start + 1
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(length))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            try:
                with path.open("rb") as fh:
                    fh.seek(start)
                    rem = length
                    while rem > 0:
                        chunk = fh.read(min(65536, rem))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        rem -= len(chunk)
            except BrokenPipeError:
                pass

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            try:
                if parsed.path == "/":
                    raw = HTML_PAGE.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self.end_headers()
                    self.wfile.write(raw)
                    return

                if parsed.path == "/api/filters":
                    self._send_json(200, {"filters": GENRE_FILTERS, "looks": LOOK_PRESETS})
                    return

                if parsed.path == "/api/voices":
                    kdir = FACELESS_HOME / "kokoro"
                    ready = (kdir / "kokoro-v1.0.onnx").exists() and (kdir / "voices-v1.0.bin").exists()
                    self._send_json(200, {"voices": VOICES, "kokoro_ready": ready})
                    return

                if parsed.path == "/api/projects":
                    self._send_json(200, {"projects": list_projects(projects_dir)})
                    return

                if parsed.path == "/api/project":
                    slug = (qs.get("slug") or [""])[0]
                    proj = resolve_project_dir(projects_dir, slug)
                    info = summarize_project(proj)
                    research = read_json(proj / "research.json", {})
                    src_count = sum(len(c.get("sources", [])) for c in research.get("claims", []))
                    self._send_json(200, {
                        **info,
                        "script": read_json(proj / "script.json", {}),
                        "script_check": run_script_check(proj),
                        "qa": read_json(proj / "review" / "qa_report.json", {}),
                        "metadata": read_json(proj / "metadata.json", {}),
                        "receipt": read_json(proj / "upload_receipt.json", {}),
                        "sources_count": src_count,
                    })
                    return

                if parsed.path == "/api/jobs":
                    slug = (qs.get("slug") or [""])[0]
                    self._send_json(200, {"jobs": jobs.list_jobs(slug)})
                    return

                if parsed.path == "/api/media":
                    slug = (qs.get("slug") or qs.get("project") or [""])[0]
                    kind = (qs.get("kind") or [""])[0]
                    proj = resolve_project_dir(projects_dir, slug)
                    if kind == "sheet":
                        self._serve_file_range(proj / "review" / "all.jpg", "image/jpeg")
                    elif kind == "narration":
                        self._serve_file_range(proj / "data" / "narration.wav", "audio/wav")
                    elif kind == "mix":
                        self._serve_file_range(proj / "data" / "mix.wav", "audio/wav")
                    elif kind == "mp4":
                        mp4 = find_master_mp4(proj)
                        if not mp4:
                            self._send_json(404, {"error": "No rendered MP4 yet"})
                        else:
                            self._serve_file_range(mp4, "video/mp4")
                    else:
                        self._send_json(400, {"error": "Invalid media type"})
                    return

                if parsed.path == "/api/upload/dry-run":
                    slug = (qs.get("slug") or [""])[0]
                    pub_at = (qs.get("publish_at") or [""])[0].strip()
                    proj = resolve_project_dir(projects_dir, slug)
                    py_bin = str(PY_WRAPPER if PY_WRAPPER.exists() else sys.executable)
                    cmd = [py_bin, str(SKILL_DIR / "scripts" / "youtube_upload.py"), str(proj), "--privacy", "private", "--dry-run"]
                    if pub_at:
                        cmd += ["--publish-at", pub_at]
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode != 0:
                        self._send_json(400, {"error": (res.stderr or res.stdout).strip()})
                    else:
                        self._send_json(200, json.loads(res.stdout))
                    return

                self._send_json(404, {"error": f"Unknown route: {parsed.path}"})
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
            except FileNotFoundError as exc:
                self._send_json(404, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            try:
                body = self._read_json_body()

                if parsed.path == "/api/create":
                    created = create_batch_drafts(projects_dir, body)
                    self._send_json(201, {"created": created})
                    return

                if parsed.path == "/api/project/script":
                    slug = body.get("slug", "")
                    proj = resolve_project_dir(projects_dir, slug)
                    script = body.get("script")
                    if not isinstance(script, dict) or not isinstance(script.get("lines"), list):
                        raise ValueError("Invalid script payload")
                    (proj / "script.json").write_text(json.dumps(script, indent=2) + "\n")
                    subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / "studio.py"), "metadata", str(proj)], capture_output=True)
                    self._send_json(200, {"saved": True, "script_check": run_script_check(proj)})
                    return

                if parsed.path == "/api/voice/audition":
                    wav_bytes = synthesize_kokoro_wav(body.get("text", ""), body.get("voice", "am_michael"), body.get("speed", 1.0))
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/wav")
                    self.send_header("Content-Length", str(len(wav_bytes)))
                    self.end_headers()
                    self.wfile.write(wav_bytes)
                    return

                if parsed.path == "/api/jobs/run":
                    slug = body.get("slug", "")
                    action = body.get("action", "")
                    proj = resolve_project_dir(projects_dir, slug)
                    steps = build_job_steps(action, proj, body)
                    job = jobs.start(proj.name, action, steps)
                    self._send_json(202, job)
                    return

                if parsed.path == "/api/upload/batch":
                    raw_slugs = body.get("slugs") or []
                    if not isinstance(raw_slugs, list) or not raw_slugs:
                        raise ValueError("Pick at least one video to upload.")
                    proj_paths = [str(resolve_project_dir(projects_dir, s)) for s in raw_slugs]
                    py_bin = str(PY_WRAPPER if PY_WRAPPER.exists() else sys.executable)
                    privacy = body.get("privacy") if body.get("privacy") in {"private", "unlisted", "public"} else "private"
                    cmd = [py_bin, str(SKILL_DIR / "scripts" / "youtube_upload.py"), *proj_paths, "--privacy", privacy]
                    pub_at = str(body.get("publish_at") or "").strip()
                    if pub_at:
                        cmd += ["--publish-at", pub_at, "--stagger-hours", str(float(body.get("stagger_hours") or 24))]
                    if body.get("force"):
                        cmd.append("--force")
                    key = f"batch-{len(proj_paths)}" if len(proj_paths) > 1 else Path(proj_paths[0]).name
                    job = jobs.start(key, f"upload ({len(proj_paths)} video{'s' if len(proj_paths) != 1 else ''})", [("YouTube upload", cmd, SKILL_DIR)])
                    self._send_json(202, job)
                    return

                self._send_json(404, {"error": f"Unknown route: {parsed.path}"})
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
            except FileNotFoundError as exc:
                self._send_json(404, {"error": str(exc)})
            except RuntimeError as exc:
                self._send_json(409, {"error": str(exc)})
            except Exception as exc:
                self._send_json(500, {"error": str(exc)})

    return StudioHandler


def run_self_test(projects_dir: Path) -> None:
    """Verify HTTP routes, category filters, path guards, and non-destructive endpoints."""
    jobs = JobManager(store_path=projects_dir / "_selftest_jobs.json")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(projects_dir, jobs))
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{port}"
        html = urllib.request.urlopen(f"{base}/").read().decode("utf-8")
        assert "33SN0W Studio" in html and "What kind of video are you thinking of?" in html

        flt = json.loads(urllib.request.urlopen(f"{base}/api/filters").read().decode("utf-8"))
        assert len(flt["filters"]) >= 7 and any(x["id"] == "horror" for x in flt["filters"])

        voices = json.loads(urllib.request.urlopen(f"{base}/api/voices").read().decode("utf-8"))
        assert len(voices["voices"]) >= 8

        projs = json.loads(urllib.request.urlopen(f"{base}/api/projects").read().decode("utf-8"))
        assert isinstance(projs["projects"], list)
        if projs["projects"]:
            slug = projs["projects"][0]["slug"]
            detail = json.loads(urllib.request.urlopen(f"{base}/api/project?slug={slug}").read().decode("utf-8"))
            assert detail["slug"] == slug and "script" in detail

        for bad_url in (f"{base}/api/project?slug=../etc",):
            try:
                urllib.request.urlopen(bad_url)
                raise AssertionError("Expected path traversal rejection")
            except urllib.error.HTTPError as err:
                assert err.code == 400

        req_bad_batch = urllib.request.Request(
            f"{base}/api/upload/batch",
            data=json.dumps({"slugs": []}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req_bad_batch)
            raise AssertionError("Expected empty batch rejection")
        except urllib.error.HTTPError as err:
            assert err.code == 400

        print(f"STUDIO_UI_SELFTEST OK (port={port}, projects={len(projs['projects'])})")
    finally:
        server.shutdown()
        server.server_close()
        (projects_dir / "_selftest_jobs.json").unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description="33SN0W Local Apple-Style Studio Web UI")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--projects-dir", default=str(DEFAULT_PROJECTS_DIR))
    p.add_argument("--open", action="store_true", help="Open the UI in the default browser")
    p.add_argument("--self-test", action="store_true", help="Run loopback HTTP API smoke check and exit")
    args = p.parse_args()

    projects_dir = Path(args.projects_dir).expanduser()
    if args.self_test:
        run_self_test(projects_dir)
        return

    jobs = JobManager()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(projects_dir, jobs))
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"33SN0W Studio running at {url} (projects: {projects_dir})", flush=True)
    if args.open:
        import webbrowser
        threading.Timer(0.4, functools.partial(webbrowser.open, url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down 33SN0W Studio...")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

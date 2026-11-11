#!/usr/bin/env python3
"""33SN0W Local Studio Review & Control Panel (pre-render approval, Kokoro voice audition,
safe-zone contact sheet & MP4 inspection, 5-axis QA scorecard, job queue & 1-click YouTube upload).

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
import subprocess
import sys
import threading
import time
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
    ("am_michael", "US Male — Steady Explainer (default)"),
    ("am_puck", "US Male — Lively, Playful"),
    ("am_fenrir", "US Male — Deeper Dramatic"),
    ("am_onyx", "US Male — Low Documentary"),
    ("af_heart", "US Female — Warm Storyteller"),
    ("af_bella", "US Female — Bright Explainer"),
    ("af_nicole", "US Female — Soft & Close"),
    ("bm_george", "UK Male — Documentary"),
    ("bm_fable", "UK Male — Storyteller"),
    ("bf_emma", "UK Female — Calm"),
]
VALID_VOICES = {v[0] for v in VOICES}

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
        raise ValueError(f"Invalid project slug: {slug!r}")
    root = projects_dir.resolve()
    target = (root / clean).resolve()
    if target.parent != root or not target.is_dir():
        raise FileNotFoundError(f"Project not found: {clean}")
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


def synthesize_kokoro_wav(text: str, voice: str = "am_michael", speed: float = 1.0) -> bytes:
    """Synthesize short audition WAV bytes in memory using local Kokoro-82M."""
    global _KOKORO_INST
    snippet = " ".join(str(text or "").split())[:420]
    if not snippet:
        raise ValueError("Provide text to audition.")
    if voice not in VALID_VOICES:
        voice = "am_michael"
    speed = max(0.65, min(1.5, float(speed or 1.0)))

    kdir = FACELESS_HOME / "kokoro"
    onnx_p = kdir / "kokoro-v1.0.onnx"
    voices_p = kdir / "voices-v1.0.bin"
    if not onnx_p.exists() or not voices_p.exists():
        raise FileNotFoundError(
            f"Kokoro models not found under {kdir}. Run: bash scripts/setup.sh (or voice.py --download)"
        )

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
    """Thread-safe local studio job runner with persistent history."""

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

    def has_running_for(self, slug: str) -> bool:
        with self._lock:
            return any(j.get("slug") == slug and j.get("status") == "running" for j in self._jobs)

    def start(self, slug: str, action: str, steps: list[tuple[str, list[str], Path]]) -> dict:
        if self.has_running_for(slug):
            raise RuntimeError(f"Another background job is already running for '{slug}'. Wait for completion.")
        job_id = uuid.uuid4().hex[:10]
        rec = {
            "id": job_id,
            "slug": slug,
            "action": action,
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

        thread = threading.Thread(target=self._run, args=(job_id, steps), daemon=True)
        thread.start()
        return dict(rec)

    def _append_log(self, job_id: str, line: str) -> None:
        with self._lock:
            for j in self._jobs:
                if j["id"] == job_id:
                    j["log"].append(line)
                    j["log"] = j["log"][-120:]
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
                self._append_log(job_id, f"$ [{label}] {' '.join(cmd)}")
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(cwd),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
                assert proc.stdout is not None
                for raw in proc.stdout:
                    line = raw.rstrip("\r\n")
                    if line:
                        self._append_log(job_id, line)
                code = proc.wait()
                if code != 0:
                    self._append_log(job_id, f"[error] step '{label}' exited with code {code}")
                    self._finish(job_id, "failed", code)
                    return
            self._append_log(job_id, "[done] all steps completed successfully.")
            self._finish(job_id, "completed", 0)
        except Exception as exc:
            self._append_log(job_id, f"[exception] {exc}")
            self._finish(job_id, "failed", 1)


def summarize_project(proj: Path) -> dict:
    script = read_json(proj / "script.json", {})
    qa = read_json(proj / "review" / "qa_report.json", {})
    receipt = read_json(proj / "upload_receipt.json", {})
    mp4 = find_master_mp4(proj)
    return {
        "slug": proj.name,
        "title": script.get("title") or proj.name.replace("-", " ").title(),
        "format": script.get("format", "unknown"),
        "artStyle": script.get("artStyle", "default"),
        "durationTier": script.get("durationTier", "standard"),
        "line_count": len(script.get("lines", [])),
        "qa_score": qa.get("total_score"),
        "qa_passed": qa.get("passed"),
        "has_sheet": (proj / "review" / "all.jpg").exists(),
        "has_mp4": mp4 is not None,
        "mp4_mb": round(mp4.stat().st_size / (1024 * 1024), 2) if mp4 else None,
        "has_narration": (proj / "data" / "narration.wav").exists(),
        "has_mix": (proj / "data" / "mix.wav").exists(),
        "uploaded": bool(receipt.get("video_id")),
        "youtube_url": receipt.get("url"),
        "privacy_status": receipt.get("privacy_status"),
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
        capture_output=True,
        text=True,
    )
    if res.stdout.strip():
        try:
            return json.loads(res.stdout)
        except Exception:
            pass
    return {"ok": res.returncode == 0, "issues": [res.stderr.strip()] if res.returncode else [], "warnings": []}


def build_job_steps(action: str, proj: Path, payload: dict) -> list[tuple[str, list[str], Path]]:
    py_bin = str(PY_WRAPPER if PY_WRAPPER.exists() else sys.executable)
    mp4_name = f"renders/{proj.name}.mp4"
    fps = str(int(payload.get("fps") or 30))
    art = str(payload.get("artStyle") or "").strip()
    art_args = ["--art-style", art] if art else []

    if action == "voice_words":
        return [
            ("voice", [py_bin, str(SKILL_DIR / "scripts" / "voice.py"), "."], proj),
            ("words", [py_bin, str(SKILL_DIR / "scripts" / "words.py"), "."], proj),
        ]
    if action == "sheet":
        return [
            ("check", ["node", "tools/capture.mjs", "check", *art_args], proj),
            ("cues", ["node", "tools/capture.mjs", "cues"], proj),
            ("sheet", ["node", "tools/capture.mjs", "sheet", "review/all.jpg", "2", "--safe-zones", *art_args], proj),
        ]
    if action == "render":
        return [
            ("cues", ["node", "tools/capture.mjs", "cues"], proj),
            ("mix", [py_bin, "tools/mix.py", "."], proj),
            ("video", ["node", "tools/capture.mjs", "video", mp4_name, "--fps", fps, *art_args], proj),
        ]
    if action == "qa_metadata":
        return [
            ("metadata", [sys.executable, str(SKILL_DIR / "scripts" / "studio.py"), "metadata", "."], proj),
            ("qa", [py_bin, str(SKILL_DIR / "scripts" / "qa_check.py"), "."], proj),
            ("analytics", [sys.executable, str(SKILL_DIR / "scripts" / "analytics.py"), "log-video", "."], proj),
        ]
    if action == "upload_private":
        cmd = [py_bin, str(SKILL_DIR / "scripts" / "youtube_upload.py"), str(proj), "--privacy", "private"]
        publish_at = str(payload.get("publish_at") or "").strip()
        if publish_at:
            cmd += ["--publish-at", publish_at]
        if payload.get("force"):
            cmd.append("--force")
        return [("youtube_upload", cmd, SKILL_DIR)]
    raise ValueError(f"Unsupported job action: {action!r}")


HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>33SN0W Studio — Review &amp; Control Panel</title>
  <style>
    :root {
      --bg: #0b1020;
      --surface: #11182c;
      --card: #172038;
      --border: #283556;
      --text: #eef2ff;
      --muted: #94a3b8;
      --accent: #38bdf8;
      --green: #34d399;
      --amber: #fbbf24;
      --red: #f87171;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }
    code, pre, textarea.mono { font-family: "SF Mono", Menlo, Monaco, monospace; }
    .shell { display: grid; grid-template-columns: 310px 1fr; min-height: 100vh; }
    aside {
      background: var(--surface);
      border-right: 1px solid var(--border);
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    main { padding: 22px 26px; overflow-x: hidden; }
    .brand { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .brand h1 { margin: 0; font-size: 17px; letter-spacing: -0.01em; }
    .btn {
      background: var(--card);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 7px 12px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn:hover { border-color: var(--accent); }
    .btn.primary { background: #0284c7; border-color: #38bdf8; color: #fff; }
    .btn.green { background: #059669; border-color: #34d399; color: #fff; }
    .btn.danger { border-color: rgba(248,113,113,.5); color: #fca5a5; }
    .btn:disabled { opacity: 0.45; cursor: not-allowed; }
    .proj-list { display: flex; flex-direction: column; gap: 8px; max-height: 46vh; overflow-y: auto; }
    .proj-item {
      text-align: left;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
      cursor: pointer;
      color: var(--text);
    }
    .proj-item.active { border-color: var(--accent); box-shadow: 0 0 0 1px rgba(56,189,248,.35); }
    .proj-item .slug { font-weight: 700; font-size: 13px; display: flex; justify-content: space-between; gap: 6px; }
    .proj-item .sub { font-size: 12px; color: var(--muted); margin-top: 3px; }
    .pill {
      display: inline-flex; align-items: center; padding: 2px 7px; border-radius: 999px;
      font-size: 11.5px; font-weight: 700; border: 1px solid var(--border); color: var(--muted);
    }
    .pill.ok { color: var(--green); border-color: rgba(52,211,153,.45); background: rgba(6,78,59,.35); }
    .pill.warn { color: var(--amber); border-color: rgba(251,191,36,.45); }
    .pill.err { color: var(--red); border-color: rgba(248,113,113,.45); }
    .panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px 18px;
      margin-bottom: 16px;
    }
    .panel h2 { margin: 0 0 10px; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }
    .row { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
    .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 16px; }
    label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; font-weight: 600; }
    input[type="text"], input[type="number"], select, textarea {
      width: 100%;
      background: var(--bg);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 13px;
    }
    textarea { resize: vertical; min-height: 54px; }
    .cut-row {
      display: grid;
      grid-template-columns: 36px 1.6fr 1fr 78px 34px;
      gap: 8px;
      align-items: start;
      padding: 8px;
      border-radius: 10px;
      background: var(--card);
      border: 1px solid var(--border);
      margin-bottom: 8px;
    }
    .hook-card {
      display: flex; gap: 10px; align-items: center; padding: 8px 10px;
      background: var(--card); border: 1px solid var(--border); border-radius: 9px; margin-bottom: 7px;
    }
    .sheet-img { width: 100%; border-radius: 10px; border: 1px solid var(--border); cursor: zoom-in; background: #000; }
    .sheet-img.zoom { position: fixed; inset: 24px; width: calc(100vw - 48px); height: calc(100vh - 48px); object-fit: contain; z-index: 60; cursor: zoom-out; }
    video.preview { width: 100%; max-height: 440px; border-radius: 10px; background: #000; border: 1px solid var(--border); }
    pre.log {
      background: #060913; border: 1px solid var(--border); border-radius: 8px;
      padding: 10px 12px; font-size: 12px; max-height: 220px; overflow-y: auto; white-space: pre-wrap; margin: 8px 0 0;
    }
    .tabs { display: flex; gap: 8px; margin-bottom: 14px; }
    .tab { padding: 8px 14px; border-radius: 9px; background: var(--card); border: 1px solid var(--border); color: var(--muted); cursor: pointer; font-weight: 600; }
    .tab.active { color: var(--text); border-color: var(--accent); background: rgba(56,189,248,.12); }
    dialog {
      background: var(--surface); color: var(--text); border: 1px solid var(--border);
      border-radius: 14px; padding: 20px; width: min(460px, 92vw);
    }
    dialog::backdrop { background: rgba(0,0,0,.65); }
    @media (max-width: 900px) { .shell { grid-template-columns: 1fr; } .cut-row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
<div class="shell">
  <aside>
    <div class="brand">
      <h1>33SN0W Studio UI</h1>
      <button class="btn primary" id="newBtn">+ New</button>
    </div>
    <div class="row" style="justify-content:space-between;font-size:12px;color:var(--muted);">
      <span id="projCount">0 projects</span>
      <button class="btn" id="refreshBtn" style="padding:4px 8px;font-size:12px;">Refresh</button>
    </div>
    <div class="proj-list" id="projList"></div>
    <div class="panel" style="margin:0;padding:12px;">
      <h2 style="font-size:13px;margin-bottom:8px;">Recent Studio Jobs</h2>
      <div id="jobsList" style="font-size:12px;color:var(--muted);max-height:28vh;overflow-y:auto;">No jobs yet.</div>
    </div>
  </aside>

  <main>
    <div id="emptyState" class="panel" style="display:none;">Select or create a project to begin reviewing.</div>
    <div id="workspace" style="display:none;">
      <div class="panel">
        <div class="row" style="justify-content:space-between;">
          <div>
            <h2 style="margin:0;font-size:18px;" id="hdrTitle">—</h2>
            <div style="font-size:12px;color:var(--muted);margin-top:3px;" id="hdrMeta">—</div>
          </div>
          <div class="row" id="hdrBadges"></div>
        </div>
      </div>

      <div class="tabs">
        <button class="tab active" data-tab="script">1. Hooks, Cuts &amp; Voice Audition</button>
        <button class="tab" data-tab="render">2. Render, Sheet &amp; QA</button>
        <button class="tab" data-tab="publish">3. Metadata &amp; YouTube Upload</button>
      </div>

      <!-- TAB 1: SCRIPT & VOICE -->
      <section id="tab-script">
        <div class="panel">
          <h2>Voiceover &amp; Kokoro Audition <span id="kokoroBadge" class="pill">—</span></h2>
          <div class="grid-2" style="grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));">
            <div><label>Title</label><input type="text" id="edTitle" /></div>
            <div><label>Voice</label><select id="edVoice"></select></div>
            <div><label>Speed (<span id="spdVal">1.0</span>x)</label><input type="range" id="edSpeed" min="0.75" max="1.35" step="0.05" value="1.0" /></div>
            <div>
              <label>Background Music</label>
              <select id="edMusic">
                <option value="bounce">bounce</option>
                <option value="bed">bed</option>
                <option value="tension">tension</option>
                <option value="none">none</option>
              </select>
            </div>
          </div>
          <div class="row" style="margin-top:12px;">
            <input type="text" id="audText" style="flex:1;min-width:220px;" placeholder="Enter any phrase (or use Hook 1) to audition voice..." />
            <button class="btn primary" id="audBtn">Audition Voice</button>
            <button class="btn" id="playNarBtn">Play Project Narration</button>
            <audio id="audAudio" controls style="height:34px;"></audio>
          </div>
        </div>

        <div class="panel">
          <h2>3 Alternative Hooks <button class="btn" id="addHookBtn" style="font-size:12px;">+ Hook</button></h2>
          <div id="hooksBox"></div>
        </div>

        <div class="panel">
          <h2>
            Editable Script Cuts (<span id="cutStats">0 lines</span>)
            <span class="row">
              <button class="btn" id="addCutBtn">+ Add Cut</button>
              <button class="btn primary" id="saveScriptBtn">Save &amp; Validate</button>
            </span>
          </h2>
          <div id="checkBanner" style="margin-bottom:10px;font-size:12.5px;"></div>
          <div id="cutsBox"></div>
        </div>
      </section>

      <!-- TAB 2: RENDER & QA -->
      <section id="tab-render" style="display:none;">
        <div class="panel">
          <h2>Local Pipeline Actions</h2>
          <div class="row">
            <button class="btn primary" data-job="voice_words">1. Generate Voice + Words</button>
            <button class="btn primary" data-job="sheet">2. Render Safe-Zone Sheet</button>
            <button class="btn green" data-job="render">3. Audio Mix + Full MP4</button>
            <button class="btn" data-job="qa_metadata">4. Refresh Metadata + 5-Axis QA</button>
          </div>
          <pre class="log" id="activeJobLog">Ready. Trigger any pipeline action above to inspect live logs.</pre>
        </div>

        <div class="grid-2">
          <div class="panel">
            <h2>Contact Sheet (<code>review/all.jpg</code>)</h2>
            <div id="sheetWrap" style="color:var(--muted);">No contact sheet rendered yet.</div>
          </div>
          <div class="panel">
            <h2>Master Video &amp; 5-Axis QA Scorecard</h2>
            <div id="videoWrap" style="margin-bottom:12px;color:var(--muted);">No MP4 rendered yet.</div>
            <div id="qaWrap" style="font-size:13px;color:var(--muted);">No QA report generated yet.</div>
          </div>
        </div>
      </section>

      <!-- TAB 3: METADATA & UPLOAD -->
      <section id="tab-publish" style="display:none;">
        <div class="grid-2">
          <div class="panel">
            <h2>YouTube Shorts Metadata Preview</h2>
            <div id="metaWrap" style="font-size:13px;color:var(--muted);">Run Metadata + QA to inspect payload.</div>
          </div>
          <div class="panel">
            <h2>1-Click Local YouTube Batch Uploader</h2>
            <div id="uploadState" style="margin-bottom:12px;"></div>
            <div style="margin-bottom:10px;">
              <label>Optional UTC Schedule (--publish-at, leave blank for immediate Private)</label>
              <input type="text" id="pubAt" placeholder="e.g. 2026-11-12T18:00:00Z" />
            </div>
            <div class="row">
              <button class="btn" id="dryRunBtn">Verify Dry-Run Payload</button>
              <button class="btn green" id="uploadPrivateBtn">Upload Private to YouTube</button>
            </div>
            <pre class="log" id="uploadDryOut" style="max-height:180px;"></pre>
          </div>
        </div>
      </section>
    </div>
  </main>
</div>

<dialog id="newModal">
  <h2 style="margin-top:0;">Scaffold New Video Project</h2>
  <div style="display:flex;flex-direction:column;gap:10px;">
    <div><label>Topic</label><input type="text" id="newTopic" placeholder="e.g. The 1919 Boston Molasses Flood" /></div>
    <div><label>Slug</label><input type="text" id="newSlug" placeholder="boston-molasses-1919" /></div>
    <div class="grid-2" style="grid-template-columns:1fr 1fr;gap:10px;">
      <div>
        <label>Format</label>
        <select id="newFmt">
          <option value="stick-story">stick-story</option>
          <option value="tall-tale">tall-tale</option>
          <option value="deep-dive">deep-dive</option>
          <option value="inside-out">inside-out</option>
          <option value="night-file">night-file</option>
          <option value="paper-atlas">paper-atlas</option>
        </select>
      </div>
      <div>
        <label>Art Style</label>
        <select id="newArt">
          <option value="default">default</option>
          <option value="comic-art">comic-art</option>
          <option value="pixel-art">pixel-art</option>
          <option value="chalkboard">chalkboard</option>
          <option value="glow-sketch">glow-sketch</option>
          <option value="ps2-retro">ps2-retro</option>
          <option value="flat-vector">flat-vector</option>
          <option value="minimal-line">minimal-line</option>
          <option value="cgi-motion">cgi-motion</option>
          <option value="lego-world">lego-world</option>
          <option value="explainer-2d">explainer-2d</option>
          <option value="vintage-film">vintage-film</option>
          <option value="claymation">claymation</option>
          <option value="watercolour">watercolour</option>
        </select>
      </div>
    </div>
    <div><label>Title</label><input type="text" id="newTitle" placeholder="The Flood That Drowned Boston in Molasses" /></div>
    <div class="row" style="justify-content:flex-end;margin-top:6px;">
      <button class="btn" id="cancelNewBtn">Cancel</button>
      <button class="btn primary" id="createNewBtn">Create Project</button>
    </div>
  </div>
</dialog>

<script>
const $ = (id) => document.getElementById(id);
let state = { projects: [], activeSlug: null, detail: null, voices: [], kokoroReady: false, pollTimer: null };

async function api(url, opts = {}) {
  const res = await fetch(url, opts);
  const ctype = res.headers.get("content-type") || "";
  if (ctype.includes("application/json")) {
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res;
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
}

async function init() {
  const v = await api("/api/voices");
  state.voices = v.voices || [];
  state.kokoroReady = !!v.kokoro_ready;
  $("edVoice").innerHTML = state.voices.map(([id, lbl]) => `<option value="${esc(id)}">${esc(id)} — ${esc(lbl)}</option>`).join("");
  $("kokoroBadge").textContent = state.kokoroReady ? "Kokoro Ready" : "Models Missing";
  $("kokoroBadge").className = "pill " + (state.kokoroReady ? "ok" : "warn");
  await refreshProjects();
  refreshJobs();
}

async function refreshProjects(selectSlug = null) {
  const data = await api("/api/projects");
  state.projects = data.projects || [];
  $("projCount").textContent = `${state.projects.length} project(s)`;
  const list = $("projList");
  list.innerHTML = "";
  if (!state.projects.length) {
    $("emptyState").style.display = "block";
    $("workspace").style.display = "none";
    return;
  }
  const target = selectSlug || state.activeSlug || state.projects[0].slug;
  state.projects.forEach((p) => {
    const btn = document.createElement("button");
    btn.className = "proj-item" + (p.slug === target ? " active" : "");
    const qaBadge = p.qa_score != null ? `<span class="pill ${p.qa_passed ? "ok" : "err"}">${p.qa_score}/100</span>` : "";
    const ytBadge = p.uploaded ? `<span class="pill ok">YT ${esc(p.privacy_status || "uploaded")}</span>` : "";
    btn.innerHTML = `
      <div class="slug"><span>${esc(p.slug)}</span><span>${qaBadge} ${ytBadge}</span></div>
      <div class="sub">${esc(p.format)} × ${esc(p.artStyle)} · ${p.line_count} cuts</div>`;
    btn.onclick = () => selectProject(p.slug);
    list.appendChild(btn);
  });
  await selectProject(target);
}

async function selectProject(slug) {
  state.activeSlug = slug;
  document.querySelectorAll(".proj-item").forEach((el, idx) => {
    el.classList.toggle("active", state.projects[idx]?.slug === slug);
  });
  $("emptyState").style.display = "none";
  $("workspace").style.display = "block";
  const detail = await api(`/api/project?slug=${encodeURIComponent(slug)}`);
  state.detail = detail;
  renderDetail(detail);
}

function renderDetail(d) {
  const s = d.script || {};
  $("hdrTitle").textContent = s.title || d.slug;
  $("hdrMeta").textContent = `${d.slug} · ${s.format || "?"} × ${s.artStyle || "default"} · tier=${s.durationTier || "standard"} · ${d.sources_count} verified URL(s)`;
  const qa = d.qa || {};
  const rec = d.receipt || {};
  $("hdrBadges").innerHTML = [
    qa.total_score != null ? `<span class="pill ${qa.passed ? "ok" : "err"}">QA ${qa.total_score}/100</span>` : `<span class="pill">QA Pending</span>`,
    rec.url ? `<a class="pill ok" style="text-decoration:none;" href="${esc(rec.url)}" target="_blank">YouTube (${esc(rec.privacy_status || "private")}) ↗</a>` : `<span class="pill">Not Uploaded</span>`
  ].join("");

  $("edTitle").value = s.title || "";
  const curVoice = s.voice || s.vo || "am_michael";
  $("edVoice").value = curVoice;
  const spd = Number(s.speed || 1.0);
  $("edSpeed").value = spd;
  $("spdVal").textContent = spd.toFixed(2);
  $("edMusic").value = s.music || "bounce";
  $("audText").value = (s.lines && s.lines[0]?.text) || (s.hooks && s.hooks[0]) || "";

  renderHooks(s.hooks || []);
  renderCuts(s.lines || []);
  renderCheck(d.script_check || {});
  renderMediaAndQa(d);
  renderMetaAndUpload(d);
}

function renderHooks(hooks) {
  const box = $("hooksBox");
  box.innerHTML = "";
  if (!hooks.length) { box.innerHTML = `<div style="color:var(--muted);font-size:12.5px;">No alternative hooks yet. Add 3 hook candidates below.</div>`; return; }
  hooks.forEach((h, i) => {
    const row = document.createElement("div");
    row.className = "hook-card";
    row.innerHTML = `
      <span class="pill">${i === 0 ? "Hook 1" : `Alt ${i + 1}`}</span>
      <input type="text" value="${esc(h)}" data-hook-idx="${i}" style="flex:1;" />
      <button class="btn" title="Copy into Cut 1">Use as Cut 1</button>
      <button class="btn" title="Audition with Kokoro">Speak</button>
      <button class="btn danger" title="Remove">×</button>`;
    const inp = row.querySelector("input");
    inp.oninput = () => { state.detail.script.hooks[i] = inp.value; };
    const [useBtn, spkBtn, delBtn] = row.querySelectorAll("button");
    useBtn.onclick = () => {
      if (!state.detail.script.lines.length) state.detail.script.lines.push({ text: "", caps: "", pause: 0.3 });
      state.detail.script.lines[0].text = inp.value;
      renderCuts(state.detail.script.lines);
      $("audText").value = inp.value;
    };
    spkBtn.onclick = () => auditionText(inp.value);
    delBtn.onclick = () => { state.detail.script.hooks.splice(i, 1); renderHooks(state.detail.script.hooks); };
    box.appendChild(row);
  });
}

function renderCuts(lines) {
  const box = $("cutsBox");
  box.innerHTML = "";
  const totalWords = lines.reduce((a, ln) => a + String(ln.text || "").trim().split(/\s+/).filter(Boolean).length, 0);
  $("cutStats").textContent = `${lines.length} cuts · ${totalWords} words`;
  lines.forEach((ln, idx) => {
    const div = document.createElement("div");
    div.className = "cut-row";
    div.innerHTML = `
      <span class="pill" style="justify-content:center;">#${idx + 1}</span>
      <div><textarea data-k="text" placeholder="Spoken narration...">${esc(ln.text || "")}</textarea></div>
      <div><input type="text" data-k="caps" value="${esc(ln.caps || "")}" placeholder="CAPS | *HIGHLIGHT" /></div>
      <div><input type="number" step="0.02" min="0" max="2" data-k="pause" value="${esc(ln.pause ?? ln.gap ?? 0.3)}" /></div>
      <button class="btn danger" style="padding:6px;">×</button>`;
    div.querySelector('[data-k="text"]').oninput = (e) => { ln.text = e.target.value; };
    div.querySelector('[data-k="caps"]').oninput = (e) => { ln.caps = e.target.value; };
    div.querySelector('[data-k="pause"]').oninput = (e) => { ln.pause = parseFloat(e.target.value || "0.3"); };
    div.querySelector("button").onclick = () => { lines.splice(idx, 1); renderCuts(lines); };
    box.appendChild(div);
  });
}

function renderCheck(chk) {
  const el = $("checkBanner");
  if (!chk || chk.word_count == null) { el.innerHTML = ""; return; }
  const errs = (chk.issues || []).map((x) => `<span class="pill err">${esc(x)}</span>`).join(" ");
  const warns = (chk.warnings || []).map((x) => `<span class="pill warn">${esc(x)}</span>`).join(" ");
  el.innerHTML = `<span class="pill ${chk.ok ? "ok" : "err"}">${chk.ok ? "Script PASS" : "Script FAIL"} (${chk.word_count}w, ~${chk.estimated_duration_sec}s)</span> ${errs} ${warns}`;
}

function renderMediaAndQa(d) {
  const ts = Date.now();
  $("sheetWrap").innerHTML = d.has_sheet
    ? `<img src="/api/media?project=${encodeURIComponent(d.slug)}&kind=sheet&t=${ts}" class="sheet-img" onclick="this.classList.toggle('zoom')" title="Click to zoom" />`
    : `No contact sheet yet. Click <strong>2. Render Safe-Zone Sheet</strong>.`;

  $("videoWrap").innerHTML = d.has_mp4
    ? `<video class="preview" controls preload="metadata" src="/api/media?project=${encodeURIComponent(d.slug)}&kind=mp4&t=${ts}"></video>`
    : `No master MP4 yet. Click <strong>3. Audio Mix + Full MP4</strong>.`;

  const qa = d.qa;
  if (!qa || qa.total_score == null) { $("qaWrap").textContent = "Run step 4 to compute the 5-axis QA score."; return; }
  const axes = Object.entries(qa.axes || {}).map(([k, v]) => `<span class="pill ${v.score === v.max ? "ok" : "warn"}">${esc(k)}: ${v.score}/${v.max}</span>`).join(" ");
  const blockers = (qa.blockers || []).length ? `<div style="margin-top:8px;color:var(--red);">Blockers: ${esc(qa.blockers.join(", "))}</div>` : "";
  $("qaWrap").innerHTML = `<div><strong>Total: ${qa.total_score}/${qa.max_score || 100}</strong> (${qa.passed ? "PASSED" : "FAILED"})</div><div class="row" style="margin-top:8px;">${axes}</div>${blockers}`;
}

function renderMetaAndUpload(d) {
  const yt = d.metadata?.youtube_shorts;
  $("metaWrap").innerHTML = yt
    ? `<div><strong>Title:</strong> ${esc(yt.recommended_title)}</div>
       <div style="margin-top:8px;"><strong>Description &amp; Hashtags:</strong><pre class="log" style="max-height:150px;">${esc(yt.description)}</pre></div>
       <div style="margin-top:8px;"><strong>Tags (${(yt.tags || []).length}):</strong> ${esc((yt.tags || []).join(", "))}</div>`
    : `Missing <code>metadata.json</code> — run step 4 first.`;

  const rec = d.receipt;
  const auth = d.oauth_ready || {};
  $("uploadState").innerHTML = `
    <div class="row">
      <span class="pill ${auth.client_secrets ? "ok" : "err"}">Secrets: ${auth.client_secrets ? "Present" : "Missing"}</span>
      <span class="pill ${auth.token ? "ok" : "warn"}">Token: ${auth.token ? "Authorized" : "Needs --auth-only"}</span>
      ${rec?.url ? `<a class="pill ok" style="text-decoration:none;" href="${esc(rec.url)}" target="_blank">Uploaded: ${esc(rec.url)} ↗</a>` : `<span class="pill">Ready for upload</span>`}
    </div>`;
}

async function auditionText(txt) {
  const text = String(txt || $("audText").value || "").trim();
  if (!text) return;
  $("audBtn").disabled = true;
  $("audBtn").textContent = "Synthesizing...";
  try {
    const res = await fetch("/api/voice/audition", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, voice: $("edVoice").value, speed: parseFloat($("edSpeed").value || "1.0") }),
    });
    if (!res.ok) throw new Error((await res.json()).error || "TTS failed");
    const blob = await res.blob();
    $("audAudio").src = URL.createObjectURL(blob);
    await $("audAudio").play();
  } catch (e) {
    alert(e.message);
  } finally {
    $("audBtn").disabled = false;
    $("audBtn").textContent = "Audition Voice";
  }
}

async function saveScript() {
  if (!state.activeSlug) return;
  const s = state.detail.script;
  s.title = $("edTitle").value.trim();
  s.voice = $("edVoice").value;
  if ("vo" in s) s.vo = s.voice;
  s.speed = parseFloat($("edSpeed").value || "1.0");
  s.music = $("edMusic").value;
  const out = await api("/api/project/script", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug: state.activeSlug, script: s }),
  });
  renderCheck(out.script_check || {});
  await refreshProjects(state.activeSlug);
}

async function triggerJob(action, extra = {}) {
  if (!state.activeSlug) return;
  const job = await api("/api/jobs/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ slug: state.activeSlug, action, ...extra }),
  });
  $("activeJobLog").textContent = `Started job ${job.id} (${action})...`;
  startPolling(job.id);
}

function startPolling(watchJobId = null) {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    const jobs = await refreshJobs();
    const hit = watchJobId ? jobs.find((j) => j.id === watchJobId) : jobs.find((j) => j.status === "running");
    if (hit) $("activeJobLog").textContent = (hit.log || []).join("\n") || `${hit.action}: ${hit.status}`;
    if (hit && hit.status !== "running") {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
      await refreshProjects(state.activeSlug);
    }
  }, 1400);
}

async function refreshJobs() {
  const data = await api("/api/jobs");
  const jobs = data.jobs || [];
  $("jobsList").innerHTML = jobs.length
    ? jobs.slice(0, 10).map((j) => `
      <div style="padding:5px 0;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;gap:6px;">
        <span><strong>${esc(j.slug)}</strong> · ${esc(j.action)}</span>
        <span class="pill ${j.status === "completed" ? "ok" : j.status === "failed" ? "err" : "warn"}">${esc(j.status)}</span>
      </div>`).join("")
    : "No jobs yet.";
  return jobs;
}

document.querySelectorAll(".tab").forEach((t) => {
  t.onclick = () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    ["script", "render", "publish"].forEach((k) => {
      $(`tab-${k}`).style.display = t.dataset.tab === k ? "block" : "none";
    });
  };
});

document.querySelectorAll("[data-job]").forEach((btn) => {
  btn.onclick = () => triggerJob(btn.dataset.job, { artStyle: state.detail?.script?.artStyle });
});

$("edSpeed").oninput = () => { $("spdVal").textContent = parseFloat($("edSpeed").value).toFixed(2); };
$("audBtn").onclick = () => auditionText($("audText").value);
$("playNarBtn").onclick = () => {
  if (!state.activeSlug) return;
  $("audAudio").src = `/api/media?project=${encodeURIComponent(state.activeSlug)}&kind=narration&t=${Date.now()}`;
  $("audAudio").play().catch(() => alert("No narration.wav found yet — run Voice + Words first."));
};
$("addHookBtn").onclick = () => { state.detail.script.hooks = state.detail.script.hooks || []; state.detail.script.hooks.push(""); renderHooks(state.detail.script.hooks); };
$("addCutBtn").onclick = () => { state.detail.script.lines.push({ text: "", caps: "", pause: 0.3 }); renderCuts(state.detail.script.lines); };
$("saveScriptBtn").onclick = saveScript;
$("refreshBtn").onclick = () => refreshProjects(state.activeSlug);

$("dryRunBtn").onclick = async () => {
  if (!state.activeSlug) return;
  const pubAt = $("pubAt").value.trim();
  const out = await api(`/api/upload/dry-run?slug=${encodeURIComponent(state.activeSlug)}&publish_at=${encodeURIComponent(pubAt)}`);
  $("uploadDryOut").textContent = JSON.stringify(out, null, 2);
};
$("uploadPrivateBtn").onclick = () => triggerJob("upload_private", { publish_at: $("pubAt").value.trim() });

$("newBtn").onclick = () => $("newModal").showModal();
$("cancelNewBtn").onclick = () => $("newModal").close();
$("createNewBtn").onclick = async () => {
  const payload = {
    topic: $("newTopic").value.trim(),
    slug: $("newSlug").value.trim(),
    format: $("newFmt").value,
    artStyle: $("newArt").value,
    title: $("newTitle").value.trim(),
  };
  if (!payload.slug) return alert("Enter a slug (e.g. boston-molasses-1919)");
  const res = await api("/api/projects/new", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  $("newModal").close();
  await refreshProjects(res.slug);
};

init().catch((e) => alert(e.message));
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
                raise ValueError("Payload too large")
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")

        def _serve_file_range(self, path: Path, content_type: str) -> None:
            if not path.is_file():
                self._send_json(404, {"error": f"File not found: {path.name}"})
                return
            size = path.stat().st_size
            rng = self.headers.get("Range")
            start, end = 0, size - 1
            status = 200
            if rng and rng.startswith("bytes="):
                spec = rng[6:].split(",")[0].strip()
                a, b = spec.split("-", 1)
                start = int(a) if a else max(0, size - int(b))
                end = int(b) if a and b else size - 1
                end = min(end, size - 1)
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
                    research = read_json(proj / "research.json", {})
                    src_count = sum(len(c.get("sources", [])) for c in research.get("claims", []))
                    self._send_json(200, {
                        "slug": proj.name,
                        "script": read_json(proj / "script.json", {}),
                        "script_check": run_script_check(proj),
                        "qa": read_json(proj / "review" / "qa_report.json", {}),
                        "metadata": read_json(proj / "metadata.json", {}),
                        "receipt": read_json(proj / "upload_receipt.json", {}),
                        "sources_count": src_count,
                        "has_sheet": (proj / "review" / "all.jpg").exists(),
                        "has_mp4": find_master_mp4(proj) is not None,
                        "oauth_ready": {
                            "client_secrets": (FACELESS_HOME / "youtube_client_secrets.json").exists(),
                            "token": (FACELESS_HOME / "youtube_token.json").exists(),
                        },
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
                            self._send_json(404, {"error": "No rendered MP4 found"})
                        else:
                            self._serve_file_range(mp4, "video/mp4")
                    else:
                        self._send_json(400, {"error": "Invalid media kind"})
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

                self._send_json(404, {"error": f"Unknown endpoint: {parsed.path}"})
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

                if parsed.path == "/api/project/script":
                    slug = body.get("slug", "")
                    proj = resolve_project_dir(projects_dir, slug)
                    script = body.get("script")
                    if not isinstance(script, dict) or not isinstance(script.get("lines"), list):
                        raise ValueError("Invalid script payload")
                    (proj / "script.json").write_text(json.dumps(script, indent=2) + "\n")
                    self._send_json(200, {"saved": True, "script_check": run_script_check(proj)})
                    return

                if parsed.path == "/api/voice/audition":
                    wav_bytes = synthesize_kokoro_wav(
                        body.get("text", ""),
                        body.get("voice", "am_michael"),
                        body.get("speed", 1.0),
                    )
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

                if parsed.path == "/api/projects/new":
                    raw_slug = "".join(c if c.isalnum() or c == "-" else "-" for c in str(body.get("slug", "")).lower()).strip("-")
                    if not raw_slug or raw_slug.startswith("_"):
                        raise ValueError("Provide a clean kebab-case slug (letters, digits, hyphens).")
                    fmt = str(body.get("format") or "stick-story")
                    art = str(body.get("artStyle") or "default")
                    title = str(body.get("title") or body.get("topic") or raw_slug.replace("-", " ").title())
                    cmd = [
                        "bash", str(SKILL_DIR / "scripts" / "new_video.sh"),
                        fmt, raw_slug, "--art-style", art, "--title", title, "--dir", str(projects_dir),
                    ]
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode != 0:
                        raise RuntimeError((res.stderr or res.stdout).strip())
                    self._send_json(201, {"slug": raw_slug, "path": str(projects_dir / raw_slug)})
                    return

                self._send_json(404, {"error": f"Unknown endpoint: {parsed.path}"})
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
    """Spin up ephemeral loopback UI server and exercise all non-destructive API endpoints."""
    jobs = JobManager(store_path=projects_dir / "_selftest_jobs.json")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(projects_dir, jobs))
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://127.0.0.1:{port}"
        html = urllib.request.urlopen(f"{base}/").read().decode("utf-8")
        assert "33SN0W Studio UI" in html

        voices = json.loads(urllib.request.urlopen(f"{base}/api/voices").read().decode("utf-8"))
        assert len(voices["voices"]) >= 8

        projs = json.loads(urllib.request.urlopen(f"{base}/api/projects").read().decode("utf-8"))
        assert isinstance(projs["projects"], list)
        if projs["projects"]:
            slug = projs["projects"][0]["slug"]
            detail = json.loads(urllib.request.urlopen(f"{base}/api/project?slug={slug}").read().decode("utf-8"))
            assert detail["slug"] == slug and "script" in detail

        try:
            urllib.request.urlopen(f"{base}/api/project?slug=../etc")
            raise AssertionError("Expected path traversal rejection")
        except urllib.error.HTTPError as err:
            assert err.code == 400

        job_list = json.loads(urllib.request.urlopen(f"{base}/api/jobs").read().decode("utf-8"))
        assert "jobs" in job_list
        print(f"STUDIO_UI_SELFTEST OK (port={port}, projects={len(projs['projects'])})")
    finally:
        server.shutdown()
        server.server_close()
        (projects_dir / "_selftest_jobs.json").unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description="33SN0W Local Studio Review & Control Web UI")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--projects-dir", default=str(DEFAULT_PROJECTS_DIR))
    p.add_argument("--open", action="store_true", help="Open the dashboard in the default browser")
    p.add_argument("--self-test", action="store_true", help="Run loopback HTTP API smoke check and exit")
    args = p.parse_args()

    projects_dir = Path(args.projects_dir).expanduser()
    if args.self_test:
        run_self_test(projects_dir)
        return

    jobs = JobManager()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(projects_dir, jobs))
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"33SN0W Studio UI running at {url} (projects: {projects_dir})", flush=True)
    if args.open:
        import webbrowser
        threading.Timer(0.4, functools.partial(webbrowser.open, url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Studio UI...")
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

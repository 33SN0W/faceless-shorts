#!/usr/bin/env python3
"""33SN0W Automated 5-Axis QA Gatekeeper (Factual, Story, Audio, Visual, Platform)."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BANNED_HOOKS = [
    r"^\s*hey\s+(guys|everyone|folks|there)\b",
    r"^\s*welcome\s+back\b",
    r"^\s*today\s+(we|i)\s+(are|will|am)\s+(going\s+to\s+)?(discuss|talk|look|explore)\b",
    r"^\s*in\s+this\s+video\b",
    r"^\s*let'?s\s+dive\s+into\b",
]


def load_json(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def find_render_mp4(proj: Path, explicit: str = "") -> Path | None:
    if explicit:
        ep = Path(explicit)
        return ep if ep.exists() else None
    renders = proj / "renders"
    if not renders.exists():
        return None
    mp4s = [p for p in renders.glob("*.mp4") if "draft" not in p.stem and "selftest" not in p.stem]
    if not mp4s:
        mp4s = list(renders.glob("*.mp4"))
    if not mp4s:
        return None
    mp4s.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return mp4s[0]


def check_factual(proj: Path) -> dict:
    score = 0
    findings = []
    blockers = []
    rp = proj / "research.json"
    if not rp.exists():
        return {"score": 0, "max": 20, "findings": ["Missing research.json"], "blockers": ["missing_research"]}
    r = load_json(rp)
    status = r.get("verification_status", "pending")
    claims = r.get("claims", [])
    real_sources = 0
    corroborated = 0
    for c in claims:
        srcs = [s for s in c.get("sources", []) if s.get("url") and "example.org" not in s.get("url", "")]
        if srcs:
            real_sources += len(srcs)
        if len(srcs) >= 2:
            corroborated += 1

    if status == "verified":
        score += 8
    elif status == "partial":
        score += 4
        findings.append("research.json verification_status is 'partial'.")
    else:
        findings.append(f"research.json verification_status is '{status}' (expected 'verified').")

    if claims and corroborated == len(claims):
        score += 8
    elif corroborated > 0 or real_sources > 0:
        score += 4
        findings.append(f"{corroborated}/{len(claims)} claims have >=2 independent source URLs.")
    else:
        findings.append("No verified source URLs in research.json (placeholder example.org only).")

    if "uncertain_or_disputed" in r:
        score += 4
    return {"score": min(20, score), "max": 20, "findings": findings, "blockers": blockers}


def check_story(proj: Path) -> dict:
    score = 0
    findings = []
    blockers = []
    sp = proj / "script.json"
    if not sp.exists():
        return {"score": 0, "max": 20, "findings": ["Missing script.json"], "blockers": ["missing_script"]}
    s = load_json(sp)
    lines = s.get("lines", [])
    first = (lines[0].get("text") or "").strip() if lines else ""
    banned = any(re.search(pat, first, re.I) for pat in BANNED_HOOKS)
    if banned or not first:
        blockers.append("banned_or_empty_hook")
        findings.append(f"Opening hook failed cliché/empty check: '{first}'")
    else:
        score += 6

    hooks = s.get("hooks", [])
    if len(hooks) >= 3:
        score += 4
    elif hooks:
        score += 2
        findings.append(f"Only {len(hooks)} alternative hooks recorded (target >= 3).")
    else:
        findings.append("No alternative 'hooks' list recorded in script.json.")

    if (proj / "storyboard.json").exists():
        sb = load_json(proj / "storyboard.json")
        scenes = sb.get("scenes", [])
        if scenes:
            score += 4
        else:
            findings.append("storyboard.json has 0 scenes.")
    else:
        findings.append("Missing storyboard.json.")

    if (proj / "characters.json").exists():
        score += 3
    else:
        findings.append("Missing characters.json consistency sheet.")

    words_p = proj / "data" / "words.json"
    lines_p = proj / "data" / "lines.json"
    if words_p.exists() and lines_p.exists():
        w_data = load_json(words_p)
        l_data = load_json(lines_p)
        if isinstance(l_data, list):
            w_lines = l_data
        elif isinstance(l_data, dict):
            w_lines = l_data.get("lines", [])
        elif isinstance(w_data, dict):
            w_lines = w_data.get("lines", [])
        else:
            w_lines = []
        if len(w_lines) == len(lines):
            score += 3
        else:
            findings.append(f"Word/line timing count ({len(w_lines)}) differs from script.json ({len(lines)}).")
    else:
        findings.append("Missing data/words.json or data/lines.json (run voice.py + words.py).")

    return {"score": min(20, score), "max": 20, "findings": findings, "blockers": blockers}


def check_audio(proj: Path, mp4: Path | None) -> dict:
    score = 0
    findings = []
    blockers = []
    target = mp4 if (mp4 and mp4.exists()) else (proj / "data" / "mix.wav")
    if not target.exists():
        target = proj / "data" / "narration.wav"
    if not target.exists():
        return {"score": 0, "max": 20, "findings": ["No rendered MP4, mix.wav, or narration.wav found."], "blockers": ["missing_audio"]}

    cmd = ["ffmpeg", "-v", "info", "-i", str(target), "-af", "volumedetect", "-vn", "-f", "null", "-"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    log = res.stderr
    m_mean = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", log)
    m_max = re.search(r"max_volume:\s*([-\d.]+)\s*dB", log)
    mean_db = float(m_mean.group(1)) if m_mean else -99.0
    max_db = float(m_max.group(1)) if m_max else -99.0

    if mean_db <= -55.0:
        blockers.append("silent_audio")
        findings.append(f"Audio is silent/near-silent (mean {mean_db} dB).")
    elif -22.5 <= mean_db <= -11.5:
        score += 10
    else:
        score += 5
        findings.append(f"Mean volume {mean_db} dB outside ideal Shorts target (-22 to -12 dB).")

    if max_db >= -0.1:
        findings.append(f"Peak volume {max_db} dB risks digital clipping.")
        score += 3
    else:
        score += 5

    if (proj / "data" / "mix.wav").exists():
        score += 5
    else:
        findings.append("Missing data/mix.wav SFX + music bed mix.")

    return {
        "score": min(20, score),
        "max": 20,
        "metrics": {"source": target.name, "mean_volume_db": mean_db, "max_volume_db": max_db},
        "findings": findings,
        "blockers": blockers,
    }


def check_visual(proj: Path, mp4: Path | None) -> dict:
    score = 0
    findings = []
    blockers = []
    script = load_json(proj / "script.json")

    art = script.get("artStyle", "default")
    fmt = script.get("format", "")
    # Safe zone check: updated styles center/clamp captions when artStyle != default or safeZone == true
    unsafe_legacy_native = fmt in ("night-file", "paper-atlas", "stick-story") and art == "default" and not script.get("safeZone")
    if unsafe_legacy_native:
        findings.append(f"Format '{fmt}' in 'default' without safeZone=true places captions inside mobile UI overlays.")
    else:
        score += 6

    if not mp4 or not mp4.exists():
        if (proj / "review" / "all.jpg").exists():
            score += 6
            findings.append("No MP4 rendered yet; contact sheet review/all.jpg exists.")
        else:
            findings.append("No rendered MP4 or review/all.jpg for pixel-level check.")
        return {"score": min(20, score), "max": 20, "findings": findings, "blockers": blockers}

    try:
        import numpy as np
    except ImportError:
        findings.append("numpy unavailable; skipped pixel inspection (run via scripts/py).")
        return {"score": min(20, score + 6), "max": 20, "findings": findings, "blockers": blockers}

    # Decode 12 sampled frames across the video at 108x192 RGB24
    dur_res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)],
        capture_output=True, text=True,
    )
    dur = float(dur_res.stdout.strip() or 0)
    timestamps = [round(max(0.4, min(dur - 0.6, 0.5 + (dur - 1.1) * i / 11.0)), 2) for i in range(12)] if dur > 2 else [0.2]
    frames = []
    black_count = 0
    for ts in timestamps:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(ts), "-i", str(mp4),
             "-vf", "scale=108:192,format=rgb24", "-vframes", "1", "-f", "rawvideo", "-"],
            capture_output=True,
        ).stdout
        if len(raw) >= 108 * 192 * 3:
            arr = np.frombuffer(raw[: 108 * 192 * 3], dtype=np.uint8).reshape((192, 108, 3)).astype(np.float32)
            frames.append(arr)
            if float(arr.mean()) < 4.5:
                black_count += 1

    if black_count > 0:
        blockers.append("black_frames_detected")
        findings.append(f"Detected {black_count} near-black frame(s) during main body timestamps.")
    elif frames:
        score += 8

    frozen_pairs = 0
    for a, b in zip(frames, frames[1:]):
        diff = float(np.abs(a - b).mean())
        if diff < 0.35:
            frozen_pairs += 1
    if len(frames) >= 4 and frozen_pairs >= len(frames) // 2:
        findings.append(f"{frozen_pairs} consecutive sampled frame pairs barely changed (<0.35 mean L1 diff) — check motion pacing.")
        score += 2
    elif frames:
        score += 6

    return {
        "score": min(20, score),
        "max": 20,
        "metrics": {"sampled_frames": len(frames), "black_frames": black_count, "static_pairs": frozen_pairs},
        "findings": findings,
        "blockers": blockers,
    }


def check_platform(proj: Path, mp4: Path | None) -> dict:
    score = 0
    findings = []
    blockers = []
    if (proj / "metadata.json").exists():
        score += 4
    else:
        findings.append("Missing metadata.json (run scripts/studio.py metadata).")

    if not mp4 or not mp4.exists():
        findings.append("No rendered MP4 to inspect platform specs.")
        return {"score": score, "max": 20, "findings": findings, "blockers": blockers}

    cmd = [
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(mp4)
    ]
    data = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    streams = data.get("streams", [])
    fmt = data.get("format", {})
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    dur = float(fmt.get("duration", 0))

    metrics = {"duration_sec": round(dur, 2)}
    if v:
        w, h = int(v.get("width", 0)), int(v.get("height", 0))
        metrics.update({"width": w, "height": h, "vcodec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"), "fps": v.get("r_frame_rate")})
        if w == 1080 and h == 1920:
            score += 6
        elif h > w and abs((w / max(1, h)) - (9 / 16)) < 0.02:
            score += 4
            findings.append(f"Resolution {w}x{h} is 9:16 draft, not full 1080x1920 master.")
        else:
            blockers.append("wrong_aspect_ratio")
            findings.append(f"Resolution {w}x{h} is not 9:16 portrait.")

        if v.get("codec_name") == "h264" and v.get("pix_fmt") in ("yuv420p", "yuvj420p"):
            score += 4
        else:
            findings.append(f"Video codec/pix_fmt is {v.get('codec_name')}/{v.get('pix_fmt')} (expected h264/yuv420p).")
    else:
        blockers.append("missing_video_stream")
        findings.append("No video stream in MP4.")

    if a:
        metrics.update({"acodec": a.get("codec_name"), "sample_rate": a.get("sample_rate"), "channels": a.get("channels")})
        if a.get("codec_name") == "aac" and str(a.get("sample_rate")) == "48000":
            score += 3
        else:
            findings.append(f"Audio {a.get('codec_name')} @ {a.get('sample_rate')} Hz (expected aac 48000 Hz).")
    else:
        findings.append("No audio stream in MP4.")

    if 5 <= dur <= 60.0:
        score += 3
    elif dur > 60.0:
        findings.append(f"Duration {dur:.1f}s exceeds classic 60s IG/Shorts quick-loop ceiling (note YT Shorts supports up to 3m).")
        score += 1

    return {"score": min(20, score), "max": 20, "metrics": metrics, "findings": findings, "blockers": blockers}


def main():
    p = argparse.ArgumentParser(description="33SN0W 5-Axis Automated QA Gatekeeper")
    p.add_argument("dir", help="Project folder path")
    p.add_argument("--mp4", default="", help="Optional explicit MP4 path")
    p.add_argument("--min-score", type=float, default=65.0)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    proj = Path(args.dir)
    if not proj.exists():
        raise FileNotFoundError(f"Project folder not found: {proj}")
    mp4 = find_render_mp4(proj, args.mp4)

    axes = {
        "factual": check_factual(proj),
        "story": check_story(proj),
        "audio": check_audio(proj, mp4),
        "visual": check_visual(proj, mp4),
        "platform": check_platform(proj, mp4),
    }
    total = sum(a["score"] for a in axes.values())
    blockers = [b for a in axes.values() for b in a["blockers"]]
    passed = total >= args.min_score and len(blockers) == 0

    report = {
        "project": str(proj),
        "mp4": str(mp4) if mp4 else None,
        "total_score": total,
        "max_score": 100,
        "passed": passed,
        "blockers": blockers,
        "axes": axes,
    }
    rev = proj / "review"
    rev.mkdir(parents=True, exist_ok=True)
    (rev / "qa_report.json").write_text(json.dumps(report, indent=2) + "\n")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"QA SCORE: {total}/100  [{'PASS' if passed else 'NEEDS WORK'}]")
        if mp4:
            print(f"MP4: {mp4}")
        for k, a in axes.items():
            print(f"  {k:10s} {a['score']:2d}/20" + (f"  -> {'; '.join(a['findings'])}" if a["findings"] else "  -> OK"))
        if blockers:
            print(f"BLOCKERS: {', '.join(blockers)}")

    if blockers:
        sys.exit(1)


if __name__ == "__main__":
    main()

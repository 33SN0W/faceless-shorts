#!/usr/bin/env python3
"""33SN0W Studio CLI — Creative Direction, Topic Discovery/Scoring, Script Check, Scaffolding & Metadata."""
import argparse
import datetime
import json
import math
import os
import random
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROJECTS_DIR = Path.home() / "faceless-shorts"
ANALYTICS_PATH = Path.home() / ".faceless-shorts" / "analytics.json"

FORMAT_ALIASES = {
    "tall-tale": "tall-tale",
    "tall-tale-3d": "tall-tale",
    "deep-dive": "deep-dive",
    "deep-dive-3d": "deep-dive",
    "inside-out": "inside-out",
    "stick-story": "stick-story",
    "night-file": "night-file",
    "night-file-3d": "night-file",
    "paper-atlas": "paper-atlas",
}

FORMATS = ["tall-tale", "deep-dive", "inside-out", "stick-story", "night-file", "paper-atlas"]

ART_STYLES = [
    "pixel-art", "chalkboard", "glow-sketch", "ps2-retro", "comic-art",
    "flat-vector", "minimal-line", "cgi-motion", "lego-world", "explainer-2d",
    "vintage-film", "claymation", "watercolour", "default",
]

DURATION_TIERS = {
    "short": {"min_s": 20, "max_s": 30, "min_w": 45, "max_w": 85},
    "standard": {"min_s": 35, "max_s": 45, "min_w": 85, "max_w": 135},
    "extended": {"min_s": 45, "max_s": 60, "min_w": 130, "max_w": 190},
}

FORMAT_KEYWORDS = {
    "deep-dive": [
        "swallow", "anatomy", "body", "organ", "brain", "heart", "lungs", "venom", "poison",
        "parasite", "insect", "spider", "jellyfish", "radiation", "pressure", "gravity",
        "black hole", "space", "lightning", "experiment", "hypothermia", "physics", "acid",
        "blood", "immune", "bacteria", "virus", "bite", "sting", "deep sea", "mariana",
        "volt", "volts", "voltage", "electric", "eel", "shock", "electrocute", "muscle", "biological",
    ],
    "inside-out": [
        "psychology", "cognitive", "bias", "dopamine", "sleep", "habit", "circadian",
        "placebo", "myth", "why does", "how does", "optical", "illusion", "memory",
        "caffeine", "stress", "hormone", "metabolism", "evolution", "perception", "science of",
    ],
    "stick-story": [
        "survive", "survival", "what would you do", "life hack", "escape", "quicksand",
        "rip current", "beach rescue", "rescues", "elevator", "bear", "shark", "stranded",
        "emergency", "wilderness", "choking", "drowning", "mistake", "scenario", "if you fall",
    ],
    "night-file": [
        "mystery", "unsolved", "vanished", "disappearance", "cold case", "creepy", "haunted",
        "ghost ship", "cipher", "dyatlov", "missing", "strange crime", "unexplained", "ufo",
        "signal", "dark history", "incident", "eerie", "abandoned", "lighthouse", "shipwreck",
    ],
    "paper-atlas": [
        "empire", "battle", "war", "voyage", "expedition", "ancient", "treaty", "civilization",
        "map", "conquest", "route", "silk road", "hannibal", "viking", "rome", "egypt",
        "greece", "napoleon", "colonial", "explorer", "frontier", "siege", "dynasty",
        "pilgrimage", "hajj", "cairo", "mecca", "mali", "mansa", "kingdom", "sultan", "crusade",
    ],
    "tall-tale": [
        "scam", "loophole", "bought", "sold", "stole", "heist", "hoax", "con artist",
        "fraud", "lawsuit", "bizarre", "absurd", "emperor", "mayor", "cat", "bear",
        "airline", "lottery", "bank", "plane", "lawnchair", "marathon", "emu", "poyais",
    ],
}

# Compatible (format -> ordered best matching non-default art styles + rationale)
FORMAT_ART_FIT = {
    "tall-tale": ["comic-art", "claymation", "lego-world", "vintage-film", "cgi-motion", "pixel-art"],
    "deep-dive": ["glow-sketch", "cgi-motion", "explainer-2d", "ps2-retro", "chalkboard", "minimal-line"],
    "inside-out": ["explainer-2d", "flat-vector", "chalkboard", "minimal-line", "glow-sketch", "claymation"],
    "stick-story": ["minimal-line", "chalkboard", "comic-art", "flat-vector", "pixel-art", "glow-sketch"],
    "night-file": ["vintage-film", "ps2-retro", "glow-sketch", "cgi-motion", "comic-art", "minimal-line"],
    "paper-atlas": ["watercolour", "vintage-film", "explainer-2d", "comic-art", "minimal-line", "claymation"],
}

ART_TONE_HINTS = {
    "vintage-film": ["190", "191", "192", "193", "194", "195", "196", "197", "198", "archive", "old", "century", "retro"],
    "watercolour": ["ancient", "voyage", "ocean", "map", "empire", "art", "renaissance", "expedition", "sea", "painted"],
    "glow-sketch": ["space", "electric", "brain", "nerve", "x-ray", "neon", "signal", "radiation", "venom", "cyber", "night"],
    "chalkboard": ["physics", "math", "formula", "law", "school", "explain", "paradox", "diagram", "theory"],
    "comic-art": ["heist", "scam", "stunt", "hero", "crazy", "wild", "bank", "loophole", "chaotic"],
    "explainer-2d": ["psychology", "biology", "health", "system", "why", "how", "habit", "economic"],
    "pixel-art": ["arcade", "game", "80s", "90s", "glitch", "computer", "speedrun", "8-bit"],
    "ps2-retro": ["2000s", "y2k", "early 3d", "console", "eerie", "liminal", "simulation"],
    "lego-world": ["build", "construction", "tiny", "city", "miniature", "bank", "tower", "toy"],
    "claymation": ["bizarre", "absurd", "folk", "animal", "weird", "quirky"],
    "minimal-line": ["quick", "survive", "rule", "paradox", "simple", "philosophy"],
    "cgi-motion": ["deep", "space", "planet", "aircraft", "submarine", "macro", "realistic"],
    "flat-vector": ["modern", "startup", "social", "app", "design", "everyday"],
}

BANNED_HOOKS = [
    r"^\s*hey\s+(guys|everyone|folks|there)\b",
    r"^\s*welcome\s+back\b",
    r"^\s*today\s+(we|i)\s+(are|will|am)\s+(going\s+to\s+)?(discuss|talk|look|explore)\b",
    r"^\s*in\s+this\s+video\b",
    r"^\s*let'?s\s+dive\s+into\b",
    r"^\s*don'?t\s+forget\s+to\s+(like|subscribe)\b",
]


def canon_format(fmt: str) -> str:
    if not fmt:
        return ""
    key = fmt.strip().lower()
    if key not in FORMAT_ALIASES:
        raise ValueError(f"Unknown format '{fmt}'. Choose one of: {', '.join(FORMATS)}")
    return FORMAT_ALIASES[key]


def canon_art_style(style: str) -> str:
    if not style:
        return ""
    key = style.strip().lower()
    if key not in ART_STYLES:
        raise ValueError(f"Unknown art style '{style}'. Choose one of: {', '.join(ART_STYLES)}")
    return key


def load_analytics_history() -> list:
    if ANALYTICS_PATH.exists():
        try:
            data = json.loads(ANALYTICS_PATH.read_text())
            return data.get("videos", [])
        except Exception:
            return []
    return []


def analyze_reference_media(media_path: Path) -> dict:
    """Extract visual traits from an image or video via ffmpeg + numpy (no copyrighted reproduction)."""
    if not media_path.exists():
        raise FileNotFoundError(f"Reference file not found: {media_path}")
    try:
        import numpy as np
    except ImportError:
        raise RuntimeError("numpy is required for reference analysis; run via scripts/py")

    probe_json = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(media_path)],
        capture_output=True, text=True, check=True,
    ).stdout)
    vstream = next((s for s in probe_json.get("streams", []) if s.get("codec_type") == "video"), {})
    w0, h0 = int(vstream.get("width", 160)), int(vstream.get("height", 160))
    dur = float(probe_json.get("format", {}).get("duration") or 0.0)
    seek_s = round(min(max(1.5, dur * 0.28), max(0.0, dur - 0.5)), 2) if dur > 2.0 else 0.0
    if w0 >= h0:
        rw, rh = 160, max(1, int(round(160 * h0 / max(1, w0))))
    else:
        rh, rw = 160, max(1, int(round(160 * w0 / max(1, h0))))
    cmd2 = ["ffmpeg", "-v", "error"]
    if seek_s > 0:
        cmd2 += ["-ss", str(seek_s)]
    cmd2 += ["-i", str(media_path), "-vf", f"scale={rw}:{rh},format=rgb24", "-vframes", "1", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd2, capture_output=True, check=True).stdout
    if len(raw) < rw * rh * 3:
        raise RuntimeError(f"ffmpeg decoded {len(raw)} bytes for '{media_path}', expected {rw * rh * 3}")
    arr = np.frombuffer(raw[: rw * rh * 3], dtype=np.uint8).reshape((rh, rw, 3)).astype(np.float32) / 255.0

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx = np.max(arr, axis=2)
    mn = np.min(arr, axis=2)
    sat = np.divide(mx - mn, np.maximum(mx, 1e-4))
    sat = np.where(mx > 1e-4, sat, 0.0)
    gx = np.abs(np.diff(luma, axis=1)).mean() if rw > 1 else 0.0
    gy = np.abs(np.diff(luma, axis=0)).mean() if rh > 1 else 0.0
    edge_density = float(gx + gy)
    warmth = float((r - b).mean())
    brightness = float(luma.mean())
    contrast = float(luma.std())
    saturation = float(sat.mean())
    mean_rgb = [int(round(v * 255)) for v in (r.mean(), g.mean(), b.mean())]

    # Map measured traits to closest art style preset + custom visual profile
    if brightness < 0.28 and saturation > 0.35:
        mapped_style = "glow-sketch"
        mood = "dark luminous high-contrast neon accent"
    elif brightness < 0.34 and saturation <= 0.35:
        mapped_style = "vintage-film"
        mood = "moody low-key desaturated atmospheric"
    elif saturation > 0.45 and contrast > 0.24:
        mapped_style = "comic-art" if edge_density > 0.14 else "flat-vector"
        mood = "vibrant high-contrast bold graphic"
    elif edge_density > 0.17 and brightness > 0.48:
        mapped_style = "watercolour" if warmth > 0.04 else "explainer-2d"
        mood = "bright detailed painterly / editorial"
    elif contrast < 0.17 and brightness > 0.52:
        mapped_style = "minimal-line"
        mood = "clean airy low-clutter composition"
    elif warmth > 0.06 and saturation < 0.35:
        mapped_style = "vintage-film"
        mood = "warm nostalgic archival tone"
    else:
        mapped_style = "cgi-motion"
        mood = "balanced dimensional cinematic lighting"

    return {
        "traits": {
            "brightness": round(brightness, 3),
            "contrast": round(contrast, 3),
            "saturation": round(saturation, 3),
            "warmth": round(warmth, 3),
            "edge_density": round(edge_density, 3),
            "dominant_mean_rgb": mean_rgb,
            "mood_summary": mood,
        },
        "inspired_art_style": mapped_style,
        "note": "Derived purely from aggregate palette, contrast, and edge statistics — original 33SN0W visuals without copying copyrighted characters/layouts.",
    }


def cmd_recommend(args):
    topic = (args.topic or "").strip()
    tlow = topic.lower()
    mode = args.mode
    if not mode:
        if args.reference:
            mode = "reference"
        elif args.random:
            mode = "random"
        elif args.format and args.art_style:
            mode = "explicit"
        else:
            mode = "auto"

    recent = load_analytics_history()[-5:]
    recent_combos = {(v.get("format"), v.get("artStyle")) for v in recent}
    recent_formats = [v.get("format") for v in recent]

    ref_info = None
    if args.reference:
        ref_info = analyze_reference_media(Path(args.reference))

    # Format scoring from topic keywords
    fmt_scores = {f: 0.0 for f in FORMATS}
    for fmt, kws in FORMAT_KEYWORDS.items():
        for kw in kws:
            if kw in tlow:
                fmt_scores[fmt] += 2.0 if len(kw) > 5 else 1.5
    # Avoid forcing everything into tall-tale when no strong tall-tale match
    if max(fmt_scores.values()) == 0:
        # Spread heuristic using non-keyword structural cues
        if any(w in tlow for w in ("why", "how", "science", "mind", "brain")):
            fmt_scores["inside-out"] += 1.5
        elif any(w in tlow for w in ("what if", "you swallow", "inside")):
            fmt_scores["deep-dive"] += 1.5
        elif any(w in tlow for w in ("what would", "if you", "survive")):
            fmt_scores["stick-story"] += 1.5
        elif any(w in tlow for w in ("who", "unknown", "case", "lost")):
            fmt_scores["night-file"] += 1.5
        elif any(w in tlow for w in ("year", "king", "empire", "fleet", "island")):
            fmt_scores["paper-atlas"] += 1.5
        else:
            # Penalize overused recent format so variety is preserved
            best_fresh = [f for f in FORMATS if recent_formats.count(f) == 0] or FORMATS
            fmt_scores[best_fresh[0]] += 1.0

    if args.format:
        chosen_fmt = canon_format(args.format)
    elif mode == "random":
        pool = [f for f in FORMATS if recent_formats[-2:].count(f) == 0] or FORMATS
        chosen_fmt = random.choice(pool)
    else:
        chosen_fmt = max(FORMATS, key=lambda f: (fmt_scores[f], -recent_formats[-3:].count(f)))

    # Art style selection
    if args.art_style:
        chosen_art = canon_art_style(args.art_style)
        art_reason = "Explicitly selected by user."
    elif ref_info:
        chosen_art = ref_info["inspired_art_style"]
        art_reason = f"Inspired by reference visual metrics ({ref_info['traits']['mood_summary']})."
    elif mode == "random":
        candidates = [s for s in FORMAT_ART_FIT[chosen_fmt] if (chosen_fmt, s) not in recent_combos] or FORMAT_ART_FIT[chosen_fmt]
        chosen_art = random.choice(candidates)
        art_reason = f"Random compatible selection paired with '{chosen_fmt}'."
    else:
        art_scores = {s: 0.0 for s in FORMAT_ART_FIT[chosen_fmt]}
        for idx, s in enumerate(FORMAT_ART_FIT[chosen_fmt]):
            art_scores[s] += max(0.5, 3.0 - idx * 0.45)
        for s, hints in ART_TONE_HINTS.items():
            if s in art_scores:
                for h in hints:
                    if h in tlow:
                        art_scores[s] += 1.5
        # Variety bonus if not recently paired
        for s in art_scores:
            if (chosen_fmt, s) in recent_combos:
                art_scores[s] -= 1.5
        chosen_art = max(art_scores, key=lambda s: art_scores[s])
        art_reason = f"Best tone & readability fit for '{chosen_fmt}' on this topic while keeping visual variety across 33SN0W uploads."

    res = {
        "mode": mode,
        "topic": topic,
        "format": chosen_fmt,
        "artStyle": chosen_art,
        "formatRationale": f"Matched topic domain signals ({chosen_fmt}) with scores {fmt_scores}" if not args.format else "Explicitly chosen format.",
        "artRationale": art_reason,
        "formatDoc": f"formats/{chosen_fmt if chosen_fmt in ('inside-out','stick-story','paper-atlas') else chosen_fmt + '-3d'}.md",
        "artStyleDoc": f"art-styles/{chosen_art}.md",
        "commandExample": f"bash scripts/new_video.sh {chosen_fmt} <short-name> --art-style {chosen_art}",
    }
    if ref_info:
        res["referenceAnalysis"] = ref_info

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"Mode:       {res['mode']}")
        print(f"Format:     {res['format']}  ({res['formatDoc']})")
        print(f"Art Style:  {res['artStyle']}  ({res['artStyleDoc']})")
        print(f"Rationale:  {res['artRationale']}")
        if ref_info:
            print(f"Ref Traits: {ref_info['traits']}")
        print(f"Next:       {res['commandExample']}")


def extract_keywords(text: str) -> set:
    stops = {
        "the", "a", "an", "and", "or", "for", "of", "in", "on", "to", "with", "about",
        "that", "this", "what", "when", "how", "why", "who", "is", "was", "were", "man",
        "woman", "story", "true", "crazy", "entire", "actually", "happened", "video",
        "just", "his", "her", "their", "because", "nearly", "even", "every", "everything",
        "made", "him", "dug", "eight", "fifty", "nine", "one", "two", "fourteen", "hundred",
    }
    words = re.findall(r"[a-z0-9]{3,}", text.lower())
    return {w for w in words if w not in stops}


def check_originality_data(topic: str, history_dir: Path) -> dict:
    q_kw = extract_keywords(topic)
    existing = []
    if history_dir.exists():
        for child in sorted(history_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("_"):
                continue
            blobs = [child.name.replace("-", " ")]
            for fname in ("script.json", "research.json", "metadata.json"):
                fp = child / fname
                if fp.exists():
                    try:
                        d = json.loads(fp.read_text())
                        for k in ("title", "topic", "vo", "description"):
                            if isinstance(d.get(k), str):
                                blobs.append(d[k])
                        for ln in d.get("lines", []):
                            if isinstance(ln, dict) and ln.get("text"):
                                blobs.append(ln["text"])
                    except Exception:
                        pass
            c_kw = extract_keywords(" ".join(blobs))
            if not q_kw or not c_kw:
                sim = 0.0
            else:
                inter = len(q_kw & c_kw)
                sim = inter / max(1, min(len(q_kw), len(c_kw)))
            existing.append({"project": child.name, "overlap": round(sim, 3), "shared_terms": sorted(q_kw & c_kw)[:8]})

    for v in load_analytics_history():
        v_kw = extract_keywords(v.get("topic", "") + " " + v.get("slug", ""))
        if q_kw and v_kw:
            sim = len(q_kw & v_kw) / max(1, min(len(q_kw), len(v_kw)))
            existing.append({"project": f"analytics:{v.get('slug')}", "overlap": round(sim, 3), "shared_terms": sorted(q_kw & v_kw)[:8]})

    existing.sort(key=lambda x: x["overlap"], reverse=True)
    top = existing[:5]
    max_ov = top[0]["overlap"] if top else 0.0
    status = "DUPLICATE_RISK" if max_ov >= 0.65 else ("CAUTION_OVERLAP" if max_ov >= 0.40 else "ORIGINAL")
    return {"topic": topic, "status": status, "max_overlap": max_ov, "closest_matches": top}


def cmd_check_originality(args):
    res = check_originality_data(args.topic, Path(args.history_dir))
    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"Originality Status: {res['status']} (max overlap: {res['max_overlap']})")
        for m in res["closest_matches"]:
            if m["overlap"] > 0:
                print(f"  - {m['project']}: {m['overlap']} (shared: {', '.join(m['shared_terms'])})")


def cmd_score(args):
    orig = check_originality_data(args.topic, Path(args.history_dir))
    # Weighted 7-factor score (1-10 inputs)
    # Default heuristic only used when scores not explicitly supplied; marked clearly
    explicit = all(
        getattr(args, k) is not None
        for k in ("curiosity", "originality", "emotion", "shareability", "visual", "story", "reliability")
    )
    tlow = args.topic.lower()
    h_orig = 2.0 if orig["status"] == "DUPLICATE_RISK" else (6.0 if orig["status"] == "CAUTION_OVERLAP" else 9.0)
    h_cur = 8.0 if any(c.isdigit() for c in tlow) or "$" in tlow or any(w in tlow for w in ("never", "secret", "what if", "only", "bought", "sold")) else 6.5
    h_vis = 8.0 if any(w in tlow for w in ("3d", "map", "body", "plane", "tower", "ocean", "fire", "space", "bank", "ship")) else 7.0
    factors = {
        "curiosity": float(args.curiosity if args.curiosity is not None else h_cur),
        "originality": float(args.originality if args.originality is not None else h_orig),
        "emotion": float(args.emotion if args.emotion is not None else 7.0),
        "shareability": float(args.shareability if args.shareability is not None else 7.5),
        "visual": float(args.visual if args.visual is not None else h_vis),
        "story": float(args.story if args.story is not None else 7.5),
        "reliability": float(args.reliability if args.reliability is not None else 8.0),
    }
    weights = {
        "curiosity": 0.20,
        "originality": 0.15,
        "emotion": 0.15,
        "shareability": 0.15,
        "visual": 0.15,
        "story": 0.10,
        "reliability": 0.10,
    }
    score_100 = round(sum(factors[k] * weights[k] for k in weights) * 10.0, 1)
    blocked_reason = []
    if factors["reliability"] < 6.0:
        blocked_reason.append("Factual reliability < 6/10 — do not fabricate or publish unverified claims.")
    if orig["status"] == "DUPLICATE_RISK":
        blocked_reason.append("High overlap with existing channel video.")

    verdict = "REJECT" if blocked_reason or score_100 < 55 else ("GREENLIGHT" if score_100 >= 72 else "REFINE")
    out = {
        "topic": args.topic,
        "scoring_mode": "EXPLICIT" if explicit else "MIXED_AUTO_HEURISTIC",
        "factors_out_of_10": factors,
        "composite_score_out_of_100": score_100,
        "verdict": verdict,
        "originality_check": orig,
        "warnings": blocked_reason,
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Topic Score: {score_100}/100  [{verdict}] ({out['scoring_mode']})")
        print(f"Originality: {orig['status']} (max overlap {orig['max_overlap']})")
        if blocked_reason:
            for w in blocked_reason:
                print(f"WARNING: {w}")


def resolve_project_paths(target: Path) -> tuple[Path, Path]:
    if target.is_dir():
        return target, target / "script.json"
    return target.parent, target


def cmd_check_script(args):
    proj_dir, script_path = resolve_project_paths(Path(args.target))
    if not script_path.exists():
        raise FileNotFoundError(f"Missing {script_path}")
    script = json.loads(script_path.read_text())
    tier = script.get("durationTier", "standard")
    bounds = DURATION_TIERS.get(tier, DURATION_TIERS["standard"])
    lines = script.get("lines", [])
    full_text = " ".join((ln.get("text") or "") for ln in lines).strip()
    words = full_text.split()
    wc = len(words)
    est_dur = round(wc / 2.75 + sum(ln.get("pause", 0.35) for ln in lines), 1)
    first_line = (lines[0].get("text") or "").strip() if lines else ""

    issues = []
    warnings = []
    for pat in BANNED_HOOKS:
        if re.search(pat, first_line, flags=re.IGNORECASE):
            issues.append(f"Banned cliche opening hook detected: '{first_line}'")

    hooks = script.get("hooks", [])
    if hooks and len(hooks) < 3:
        warnings.append(f"Only {len(hooks)} hook candidates in script.json; standard requires 3 alternative hooks.")
    elif not hooks:
        warnings.append("No 'hooks' array in script.json (add 3 alternative hooks for testing/logging).")

    rhetorical_qs = sum(1 for ln in lines[1:] if (ln.get("text") or "").strip().endswith("?"))
    if rhetorical_qs >= 2:
        warnings.append(f"{rhetorical_qs} rhetorical questions in body lines; avoid repetitive rhetorical questions.")

    if wc < bounds["min_w"] or wc > bounds["max_w"]:
        warnings.append(f"Word count {wc} outside '{tier}' tier target ({bounds['min_w']}-{bounds['max_w']} words).")
    if est_dur < bounds["min_s"] or est_dur > bounds["max_s"]:
        warnings.append(f"Estimated duration {est_dur}s outside '{tier}' tier target ({bounds['min_s']}-{bounds['max_s']}s).")

    # Check sentence punchiness
    sents = [s.strip() for s in re.split(r"[.!?]+", full_text) if s.strip()]
    long_sents = [s for s in sents if len(s.split()) > 22]
    if long_sents:
        warnings.append(f"{len(long_sents)} sentence(s) exceed 22 words — shorten for crisp conversational Shorts pacing.")

    # Supporting files check
    for req in ("research.json", "characters.json", "storyboard.json"):
        p = proj_dir / req
        if not p.exists():
            warnings.append(f"Missing studio file: {req}")

    sb_path = proj_dir / "storyboard.json"
    if sb_path.exists():
        try:
            sb = json.loads(sb_path.read_text())
            scenes = sb.get("scenes", sb if isinstance(sb, list) else [])
            req_fields = {
                "scene_id", "beat", "duration_sec", "narration_line", "visual_description",
                "characters_present", "setting_environment", "lighting_mood",
                "camera_angle", "camera_movement", "focal_point",
                "transition_in", "transition_out", "on_screen_text",
            }
            for idx, sc in enumerate(scenes):
                missing = sorted(req_fields - set(sc.keys()))
                if missing:
                    warnings.append(f"storyboard.json scene[{idx}] missing fields: {', '.join(missing)}")
                    break
        except Exception as e:
            issues.append(f"Invalid storyboard.json: {e}")

    ok = len(issues) == 0
    out = {
        "ok": ok,
        "project": str(proj_dir),
        "duration_tier": tier,
        "line_count": len(lines),
        "word_count": wc,
        "estimated_duration_sec": est_dur,
        "first_line": first_line,
        "issues": issues,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Script Check: {'PASS' if ok else 'FAIL'} ({wc} words, ~{est_dur}s, tier={tier})")
        for x in issues:
            print(f"  ERROR: {x}")
        for w in warnings:
            print(f"  WARN:  {w}")
    if not ok:
        sys.exit(1)


def cmd_scaffold(args):
    proj_dir = Path(args.dir)
    proj_dir.mkdir(parents=True, exist_ok=True)
    fmt = canon_format(args.format)
    art = canon_art_style(args.art_style or "default")
    tier = args.duration or "standard"
    title = args.title or proj_dir.name.replace("-", " ").title()

    sp = proj_dir / "script.json"
    if sp.exists():
        data = json.loads(sp.read_text())
        data["format"] = fmt
        data["artStyle"] = art
        data["durationTier"] = tier
        if not args.no_safe_zone:
            data["safeZone"] = True
        if args.title:
            data["title"] = title
        if args.fps:
            data["fps"] = args.fps
        if "hooks" not in data:
            first_t = (data.get("lines", [{}])[0].get("text") or "").strip()
            data["hooks"] = [first_t] if first_t else []
        sp.write_text(json.dumps(data, indent=2) + "\n")

    today = datetime.date.today().isoformat()
    research_p = proj_dir / "research.json"
    if not research_p.exists():
        research_p.write_text(json.dumps({
            "topic": title,
            "slug": proj_dir.name,
            "created_at": today,
            "verification_status": "pending",
            "claims": [
                {
                    "claim": "Replace with factual claim verified from >=2 independent reputable sources.",
                    "confidence": "verified",
                    "sources": [
                        {"title": "Primary/Secondary Source", "url": "https://example.org", "tier": "primary"}
                    ],
                }
            ],
            "uncertain_or_disputed": [],
            "topic_score": {},
        }, indent=2) + "\n")

    chars_p = proj_dir / "characters.json"
    if not chars_p.exists():
        chars_p.write_text(json.dumps({
            "format": fmt,
            "artStyle": art,
            "characters": [
                {
                    "id": "lead_subject",
                    "name": "Primary Subject",
                    "silhouette": "Distinctive consistent head/body silhouette and posture.",
                    "palette": {"primary": "#2B4C7E", "accent": "#E85D04", "skin_or_surface": "#F2C6A0"},
                    "clothing_or_features": "Consistent signature outfit or structural feature across all shots.",
                    "props": [],
                    "never_change_rules": ["Keep proportions, outfit color, and signature silhouette identical across scenes."],
                }
            ],
        }, indent=2) + "\n")

    sb_p = proj_dir / "storyboard.json"
    if not sb_p.exists():
        lines = []
        if sp.exists():
            lines = json.loads(sp.read_text()).get("lines", [])
        scenes = []
        beats = ["hook", "context", "escalation", "payoff", "ending"]
        for i, ln in enumerate(lines):
            beat = beats[min(len(beats) - 1, int(i * len(beats) / max(1, len(lines))))]
            scenes.append({
                "scene_id": f"S{i + 1:02d}",
                "beat": beat,
                "duration_sec": round(len((ln.get("text") or "").split()) / 2.75 + ln.get("pause", 0.35), 2),
                "narration_line": ln.get("text", ""),
                "visual_description": f"Visual depiction of beat '{beat}' in {fmt} + {art} style.",
                "characters_present": ["lead_subject"],
                "setting_environment": "Scene-matched grounded environment",
                "lighting_mood": "Matched to storytelling beat",
                "camera_angle": "eye-level" if i % 2 == 0 else "low-angle push",
                "camera_movement": "slow push-in" if i == 0 else "smooth pan",
                "focal_point": "Central action inside mobile safe zone (x 70-940, y 280-1470)",
                "transition_in": "hard-cut" if i == 0 else "match-cut",
                "transition_out": "whip-cut" if i < len(lines) - 1 else "fade-loop",
                "on_screen_text": ln.get("caps", ""),
            })
        sb_p.write_text(json.dumps({"title": title, "format": fmt, "artStyle": art, "scenes": scenes}, indent=2) + "\n")

    print(json.dumps({"scaffolded": str(proj_dir), "format": fmt, "artStyle": art, "durationTier": tier}, indent=2))


def cmd_metadata(args):
    proj_dir = Path(args.dir)
    sp = proj_dir / "script.json"
    if not sp.exists():
        raise FileNotFoundError(f"Missing {sp}")
    script = json.loads(sp.read_text())
    research = {}
    rp = proj_dir / "research.json"
    if rp.exists():
        research = json.loads(rp.read_text())

    topic = script.get("title") or research.get("topic") or proj_dir.name.replace("-", " ").title()
    fmt = script.get("format", "tall-tale")
    art = script.get("artStyle", "default")
    hook = (script.get("lines", [{}])[0].get("text") or topic).strip()
    base_short = re.sub(r"\s+", " ", topic).strip()
    if len(base_short) > 56:
        base_short = base_short[:53].rsplit(" ", 1)[0]

    alt2 = f"Why {base_short} Happened" if base_short.lower().startswith("how ") else f"How {base_short} Actually Happened"
    titles = [
        base_short[:60],
        alt2[:60],
        f"True Story: {base_short}"[:60],
    ]
    # Collect verified source URLs cleanly
    src_urls = []
    for c in research.get("claims", []):
        for s in c.get("sources", []):
            u = s.get("url", "")
            if u and "example.org" not in u and u not in src_urls:
                src_urls.append(u)

    sources_block = "\n\nSources:\n" + "\n".join(f"- {u}" for u in src_urls[:4]) if src_urls else ""
    kw_set = sorted(extract_keywords(topic + " " + hook))[:8]
    tags = ["33SN0W", "history", "weird history", "true story", "shorts"] + kw_set
    hashtags_yt = "#shorts #history #weirdhistory #truestory #33SN0W"
    hashtags_ig = "#reels #shorts #history #weirdhistory #33SN0W"

    meta = {
        "channel": "33SN0W",
        "slug": proj_dir.name,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "format": fmt,
        "artStyle": art,
        "youtube_shorts": {
            "title_options": titles,
            "recommended_title": titles[0],
            "description": f"{hook}{sources_block}\n\n{hashtags_yt}",
            "tags": tags,
            "search_keywords": kw_set,
            "ai_synthetic_disclosure": {
                "recommend_disclosure_flag": True,
                "reason": "Narration uses Kokoro neural TTS synthetic speech; stylized non-photoreal procedural animation normally does not trigger deepfake realism rules, but disclosing synthetic voiceover preserves transparency under YouTube altered/synthetic media guidelines.",
            },
        },
        "instagram_reels": {
            "caption": f"{hook}\n\nWould you have spotted this? Save or share if this surprised you.\n\n{hashtags_ig}",
            "cover_frame_tip": "Pick the highest-contrast frame between 0.3s and 1.2s inside y=280..1470 safe zone.",
        },
        "pinned_comment": f"Which detail of '{base_short}' surprised you the most?",
    }
    mp = proj_dir / "metadata.json"
    mp.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Wrote {mp}")


def main():
    p = argparse.ArgumentParser(description="33SN0W AI Shorts Studio CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("recommend", help="Choose format + art style (explicit, auto, random, reference)")
    r.add_argument("--topic", default="", help="Video topic or premise")
    r.add_argument("--format", default="", help="Explicit format override")
    r.add_argument("--art-style", default="", help="Explicit art style override")
    r.add_argument("--mode", choices=["explicit", "auto", "random", "reference"], default="")
    r.add_argument("--random", action="store_true")
    r.add_argument("--reference", default="", help="Path to reference image or video")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_recommend)

    o = sub.add_parser("check-originality", help="Compare topic against existing channel videos")
    o.add_argument("--topic", required=True)
    o.add_argument("--history-dir", default=str(DEFAULT_PROJECTS_DIR))
    o.add_argument("--json", action="store_true")
    o.set_defaults(func=cmd_check_originality)

    sc = sub.add_parser("score", help="Compute 7-factor topic potential score (0-100)")
    sc.add_argument("--topic", required=True)
    sc.add_argument("--history-dir", default=str(DEFAULT_PROJECTS_DIR))
    for f in ("curiosity", "originality", "emotion", "shareability", "visual", "story", "reliability"):
        sc.add_argument(f"--{f}", type=float, default=None)
    sc.add_argument("--json", action="store_true")
    sc.set_defaults(func=cmd_score)

    cs = sub.add_parser("check-script", help="Validate script hooks, pacing, tier duration & storyboard")
    cs.add_argument("target", help="Project folder or script.json")
    cs.add_argument("--json", action="store_true")
    cs.set_defaults(func=cmd_check_script)

    sf = sub.add_parser("scaffold", help="Create research.json, characters.json, storyboard.json & update script.json")
    sf.add_argument("dir")
    sf.add_argument("--format", required=True)
    sf.add_argument("--art-style", default="default")
    sf.add_argument("--duration", default="standard", choices=["short", "standard", "extended"])
    sf.add_argument("--title", default="")
    sf.add_argument("--fps", type=int, default=30)
    sf.add_argument("--no-safe-zone", action="store_true")
    sf.set_defaults(func=cmd_scaffold)

    md = sub.add_parser("metadata", help="Generate multi-platform YouTube Shorts + IG Reels metadata.json")
    md.add_argument("dir")
    md.set_defaults(func=cmd_metadata)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

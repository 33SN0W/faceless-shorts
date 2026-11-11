#!/usr/bin/env python3
"""33SN0W Analytics & Anti-Vanity Performance Learning Loop."""
import argparse
import datetime
import json
from collections import defaultdict
from pathlib import Path

ANALYTICS_PATH = Path.home() / ".faceless-shorts" / "analytics.json"


def load_store() -> dict:
    if ANALYTICS_PATH.exists():
        try:
            return json.loads(ANALYTICS_PATH.read_text())
        except Exception:
            pass
    return {"channel": "33SN0W", "updated_at": None, "videos": []}


def save_store(data: dict) -> None:
    ANALYTICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    ANALYTICS_PATH.write_text(json.dumps(data, indent=2) + "\n")


def read_json(p: Path) -> dict:
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def cmd_log_video(args):
    proj = Path(args.dir)
    if not proj.exists():
        raise FileNotFoundError(f"Project folder not found: {proj}")
    script = read_json(proj / "script.json")
    research = read_json(proj / "research.json")
    cues = read_json(proj / "data" / "cues.json")
    words_meta = read_json(proj / "data" / "words.json")
    qa = read_json(proj / "review" / "qa_report.json")

    slug = proj.name
    topic = script.get("title") or research.get("topic") or slug.replace("-", " ").title()
    fmt = script.get("format", args.format or "unknown")
    art = script.get("artStyle", args.art_style or "default")
    tier = script.get("durationTier", "standard")
    lines = script.get("lines", [])
    hook = (lines[0].get("text") or "").strip() if lines else ""
    hook_type = args.hook_type or script.get("hookType") or ("question" if hook.endswith("?") else "premise")
    dur = (cues.get("duration") if isinstance(cues, dict) else 0.0) or (words_meta.get("dur") if isinstance(words_meta, dict) else 0.0) or 0.0

    store = load_store()
    videos = store.setdefault("videos", [])
    existing = next((v for v in videos if v.get("slug") == slug), None)

    entry = existing or {"slug": slug, "metrics": None}
    entry.update({
        "slug": slug,
        "project_dir": str(proj),
        "topic": topic,
        "format": fmt,
        "artStyle": art,
        "durationTier": tier,
        "duration_sec": round(float(dur), 2) if dur else entry.get("duration_sec", 0.0),
        "hook": hook,
        "hookType": hook_type,
        "qa_score": qa.get("total_score", entry.get("qa_score")),
        "logged_at": datetime.datetime.now().isoformat(timespec="seconds"),
    })
    if not existing:
        videos.append(entry)

    save_store(store)
    print(json.dumps({"logged": entry, "store": str(ANALYTICS_PATH)}, indent=2))


def cmd_import_metrics(args):
    store = load_store()
    videos = store.setdefault("videos", [])
    entry = next((v for v in videos if v.get("slug") == args.slug), None)
    if not entry:
        entry = {"slug": args.slug, "topic": args.slug, "format": "unknown", "artStyle": "default", "logged_at": datetime.datetime.now().isoformat(timespec="seconds")}
        videos.append(entry)

    if args.json_file:
        m = json.loads(Path(args.json_file).read_text())
    else:
        views = max(0, args.views or 0)
        engaged = args.engaged_views if args.engaged_views is not None else views
        denom = max(1, engaged)
        m = {
            "views": views,
            "engaged_views": engaged,
            "stayed_to_watch_pct": args.stayed_to_watch,
            "avg_pct_viewed": args.avg_pct_viewed,
            "likes": args.likes or 0,
            "shares": args.shares or 0,
            "saves": args.saves or 0,
            "comments": args.comments or 0,
            "shares_per_1k_engaged": round(((args.shares or 0) / denom) * 1000, 2),
            "saves_per_1k_engaged": round(((args.saves or 0) / denom) * 1000, 2),
            "imported_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
    entry["metrics"] = m
    save_store(store)
    print(json.dumps({"updated": args.slug, "metrics": m}, indent=2))


def quality_index(v: dict) -> float | None:
    m = v.get("metrics")
    if not m:
        return None
    # Anti-vanity score: prioritize stayed_to_watch, avg_pct_viewed, shares & saves per 1k engaged
    stayed = float(m.get("stayed_to_watch_pct") or 0)
    apv = float(m.get("avg_pct_viewed") or 0)
    shares_k = float(m.get("shares_per_1k_engaged") or 0)
    saves_k = float(m.get("saves_per_1k_engaged") or 0)
    return round(stayed * 0.4 + min(120.0, apv) * 0.4 + min(40.0, shares_k) * 0.5 + min(40.0, saves_k) * 0.4, 2)


def group_stats(videos: list, field: str) -> dict:
    buckets = defaultdict(list)
    for v in videos:
        buckets[v.get(field) or "unknown"].append(v)
    out = {}
    for k, items in sorted(buckets.items()):
        with_m = [v for v in items if v.get("metrics")]
        qis = [q for q in (quality_index(v) for v in with_m) if q is not None]
        out[k] = {
            "count": len(items),
            "with_metrics": len(with_m),
            "avg_qa_score": round(sum(v["qa_score"] for v in items if v.get("qa_score") is not None) / max(1, sum(1 for v in items if v.get("qa_score") is not None)), 1) if any(v.get("qa_score") is not None for v in items) else None,
            "avg_quality_index": round(sum(qis) / len(qis), 2) if qis else None,
        }
    return out


def cmd_summary(args):
    store = load_store()
    videos = store.get("videos", [])
    out = {
        "total_logged_videos": len(videos),
        "videos_with_platform_metrics": sum(1 for v in videos if v.get("metrics")),
        "by_format": group_stats(videos, "format"),
        "by_artStyle": group_stats(videos, "artStyle"),
        "by_hookType": group_stats(videos, "hookType"),
        "by_durationTier": group_stats(videos, "durationTier"),
    }
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Logged videos: {out['total_logged_videos']}  (with platform metrics: {out['videos_with_platform_metrics']})")
        for section in ("by_format", "by_artStyle", "by_durationTier"):
            print(f"\n[{section}]")
            for k, val in out[section].items():
                print(f"  {k:16s} count={val['count']} metrics={val['with_metrics']} qa={val['avg_qa_score']} anti_vanity_idx={val['avg_quality_index']}")


def cmd_recommend(args):
    store = load_store()
    videos = store.get("videos", [])
    with_m = [v for v in videos if v.get("metrics") and quality_index(v) is not None]
    all_formats = {"tall-tale", "deep-dive", "inside-out", "stick-story", "night-file", "paper-atlas"}
    used_formats = {v.get("format") for v in videos}
    unexplored_formats = sorted(all_formats - used_formats)

    out = {
        "sample_size_logged": len(videos),
        "sample_size_with_metrics": len(with_m),
        "confidence": "insufficient_metrics (<3 videos with imported analytics)" if len(with_m) < 3 else "empirical",
        "unexplored_formats": unexplored_formats,
        "recent_combos": [[v.get("format"), v.get("artStyle")] for v in videos[-5:]],
        "recommendations": [],
    }
    if len(with_m) < 3:
        out["recommendations"].append(
            "Import real YouTube Studio / IG Insights metrics for at least 3 Shorts via `analytics.py import-metrics` before weighting empirical winners; prioritize untested formats to build baseline signal."
        )
    else:
        ranked = sorted(with_m, key=lambda v: quality_index(v) or 0, reverse=True)
        top = ranked[0]
        out["top_performing_pattern"] = {
            "slug": top.get("slug"),
            "format": top.get("format"),
            "artStyle": top.get("artStyle"),
            "hookType": top.get("hookType"),
            "anti_vanity_index": quality_index(top),
        }
        out["recommendations"].append(
            f"Top anti-vanity retention performer so far: {top.get('format')} x {top.get('artStyle')} ({top.get('hookType')} hook, index={quality_index(top)})."
        )
    if unexplored_formats:
        out["recommendations"].append(f"Channel diversity gap — try untested formats: {', '.join(unexplored_formats)}.")

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"Confidence: {out['confidence']}")
        for r in out["recommendations"]:
            print(f" - {r}")


def main():
    p = argparse.ArgumentParser(description="33SN0W Analytics & Learning Engine")
    sub = p.add_subparsers(dest="cmd", required=True)

    lv = sub.add_parser("log-video", help="Log a generated project into ~/.faceless-shorts/analytics.json")
    lv.add_argument("dir")
    lv.add_argument("--format", default="")
    lv.add_argument("--art-style", default="")
    lv.add_argument("--hook-type", default="")
    lv.set_defaults(func=cmd_log_video)

    im = sub.add_parser("import-metrics", help="Import real YT Shorts / IG Reels metrics for a video slug")
    im.add_argument("slug")
    im.add_argument("--json-file", default="")
    im.add_argument("--views", type=int, default=0)
    im.add_argument("--engaged-views", type=int, default=None)
    im.add_argument("--stayed-to-watch", type=float, default=0.0, help="Percentage who chose to view vs swipe away")
    im.add_argument("--avg-pct-viewed", type=float, default=0.0)
    im.add_argument("--likes", type=int, default=0)
    im.add_argument("--shares", type=int, default=0)
    im.add_argument("--saves", type=int, default=0)
    im.add_argument("--comments", type=int, default=0)
    im.set_defaults(func=cmd_import_metrics)

    sm = sub.add_parser("summary", help="Aggregate channel performance across formats & art styles")
    sm.add_argument("--json", action="store_true")
    sm.set_defaults(func=cmd_summary)

    rc = sub.add_parser("recommend", help="Data-backed production recommendations")
    rc.add_argument("--json", action="store_true")
    rc.set_defaults(func=cmd_recommend)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

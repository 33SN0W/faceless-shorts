#!/usr/bin/env python3
"""33SN0W Local YouTube Shorts Batch Uploader (YouTube Data API v3 + OAuth 2.0).

Stores OAuth client secrets & refresh tokens safely outside the git workspace under
~/.faceless-shorts/ with 0600 permissions. Supports dry-run validation, QA gating,
resumable chunked uploads, idempotent upload receipts, and staggered scheduling.
"""
import argparse
import datetime
import json
import os
import stat
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROJECTS_DIR = Path.home() / "faceless-shorts"
DEFAULT_SECRETS = Path.home() / ".faceless-shorts" / "youtube_client_secrets.json"
DEFAULT_TOKEN = Path.home() / ".faceless-shorts" / "youtube_token.json"
ANALYTICS_PATH = Path.home() / ".faceless-shorts" / "analytics.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def resolve_project_dir(item: str) -> Path:
    p = Path(item).expanduser()
    if p.exists():
        return p.resolve()
    alt = DEFAULT_PROJECTS_DIR / item
    if alt.exists():
        return alt.resolve()
    raise FileNotFoundError(f"Project folder not found: '{item}' (checked '{p}' and '{alt}')")


def find_master_mp4(proj: Path) -> Path:
    renders = proj / "renders"
    preferred = renders / f"{proj.name}.mp4"
    if preferred.exists():
        return preferred
    mp4s = [x for x in renders.glob("*.mp4") if "draft" not in x.stem and "selftest" not in x.stem] if renders.exists() else []
    if not mp4s:
        raise FileNotFoundError(f"No rendered master MP4 found in {renders}")
    mp4s.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return mp4s[0]


def clamp_tags(tags: list[str], budget: int = 420) -> list[str]:
    clean, total = [], 0
    for t in tags:
        s = str(t).strip().replace("<", "").replace(">", "")
        if not s or s.lower() in {x.lower() for x in clean}:
            continue
        cost = len(s) + (3 if " " in s else 1)
        if total + cost > budget:
            break
        clean.append(s)
        total += cost
    return clean


def build_payload(proj: Path, args, publish_iso: str | None) -> dict:
    mp4 = find_master_mp4(proj)
    meta = load_json(proj / "metadata.json")
    yt = meta.get("youtube_shorts", {})
    if not yt:
        raise RuntimeError(f"Missing youtube_shorts in {proj / 'metadata.json'}. Run: python3 scripts/studio.py metadata {proj}")

    qa = load_json(proj / "review" / "qa_report.json")
    if not args.force:
        if not qa:
            raise RuntimeError(f"Missing QA report ({proj / 'review' / 'qa_report.json'}). Run qa_check.py first or pass --force.")
        if not qa.get("passed"):
            raise RuntimeError(f"QA failed for {proj.name} ({qa.get('total_score')}/100). Fix blockers or pass --force.")

    title = (yt.get("recommended_title") or proj.name.replace("-", " ").title()).strip()[:100]
    desc = (yt.get("description") or "").strip()
    if "#shorts" not in desc.lower():
        desc = f"{desc}\n\n#shorts".strip()
    desc = desc[:5000]
    tags = clamp_tags(yt.get("tags", ["shorts", "33SN0W", "history"]))

    ai_flag = bool(yt.get("ai_synthetic_disclosure", {}).get("recommend_disclosure_flag", True))
    if args.no_synthetic_flag:
        ai_flag = False

    privacy = "private" if publish_iso else args.privacy
    status = {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": bool(args.made_for_kids),
    }
    if publish_iso:
        status["publishAt"] = publish_iso
    if ai_flag:
        status["containsSyntheticMedia"] = True

    return {
        "project": proj,
        "slug": proj.name,
        "mp4": mp4,
        "size_mb": round(mp4.stat().st_size / (1024 * 1024), 2),
        "qa_score": qa.get("total_score"),
        "body": {
            "snippet": {
                "title": title,
                "description": desc,
                "tags": tags,
                "categoryId": args.category_id,
                "defaultLanguage": "en",
                "defaultAudioLanguage": "en",
            },
            "status": status,
        },
    }


def get_youtube_service(secrets_path: Path, token_path: Path):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as e:
        raise RuntimeError(f"Missing Google API dependencies ({e}). Run via ./scripts/py scripts/youtube_upload.py")

    if not secrets_path.exists():
        raise FileNotFoundError(
            f"OAuth client secrets not found at '{secrets_path}'.\n"
            "Download your Desktop App OAuth JSON from Google Cloud Console (YouTube Data API v3)\n"
            f"and save it to: {secrets_path}"
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0, prompt="consent")
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())
        os.chmod(token_path, stat.S_IRUSR | stat.S_IWUSR)

    return build("youtube", "v3", credentials=creds)


def record_analytics_upload(slug: str, video_id: str, url: str, privacy: str):
    if not ANALYTICS_PATH.exists():
        return
    try:
        data = json.loads(ANALYTICS_PATH.read_text())
        for v in data.get("videos", []):
            if v.get("slug") == slug:
                v["youtube_video_id"] = video_id
                v["youtube_url"] = url
                v["privacy_status"] = privacy
                v["uploaded_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        ANALYTICS_PATH.write_text(json.dumps(data, indent=2) + "\n")
    except Exception:
        pass


def upload_one(youtube, plan: dict, playlist_id: str = "") -> dict:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    body = json.loads(json.dumps(plan["body"]))
    media = MediaFileUpload(str(plan["mp4"]), mimetype="video/mp4", chunksize=4 * 1024 * 1024, resumable=True)

    def run_insert(req_body):
        req = youtube.videos().insert(part="snippet,status", body=req_body, media_body=media)
        resp = None
        while resp is None:
            status, resp = req.next_chunk()
            if status:
                print(f"  [{plan['slug']}] uploaded {int(status.progress() * 100)}%", flush=True)
        return resp

    try:
        resp = run_insert(body)
    except HttpError as e:
        msg = str(e)
        if "containsSyntheticMedia" in msg and "containsSyntheticMedia" in body["status"]:
            print(f"  [{plan['slug']}] retrying without containsSyntheticMedia property (not accepted for this project tier)...", file=sys.stderr)
            body["status"].pop("containsSyntheticMedia", None)
            media = MediaFileUpload(str(plan["mp4"]), mimetype="video/mp4", chunksize=4 * 1024 * 1024, resumable=True)
            resp = run_insert(body)
        else:
            raise

    vid = resp["id"]
    url = f"https://youtube.com/shorts/{vid}"

    if playlist_id:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": vid},
                }
            },
        ).execute()

    receipt = {
        "slug": plan["slug"],
        "video_id": vid,
        "url": url,
        "title": body["snippet"]["title"],
        "privacy_status": resp.get("status", {}).get("privacyStatus", body["status"]["privacyStatus"]),
        "publish_at": body["status"].get("publishAt"),
        "uploaded_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    (plan["project"] / "upload_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    record_analytics_upload(plan["slug"], vid, url, receipt["privacy_status"])
    return receipt


def main():
    p = argparse.ArgumentParser(description="33SN0W Local YouTube Shorts Batch Uploader")
    p.add_argument("projects", nargs="*", help="Project slugs or paths (e.g. pig-war-1859 ...)")
    p.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
    p.add_argument("--publish-at", default="", help="Optional ISO-8601 UTC schedule start (e.g. 2026-11-12T18:00:00Z)")
    p.add_argument("--stagger-hours", type=float, default=24.0, help="Hours between scheduled videos when --publish-at is used")
    p.add_argument("--category-id", default="27", help="YouTube category ID (27=Education, 24=Entertainment)")
    p.add_argument("--playlist-id", default="", help="Optional YouTube Playlist ID to add uploaded videos to")
    p.add_argument("--made-for-kids", action="store_true")
    p.add_argument("--no-synthetic-flag", action="store_true")
    p.add_argument("--client-secrets", default=str(DEFAULT_SECRETS))
    p.add_argument("--token", default=str(DEFAULT_TOKEN))
    p.add_argument("--auth-only", action="store_true", help="Authenticate & verify channel identity without uploading")
    p.add_argument("--dry-run", action="store_true", help="Validate MP4s, QA, metadata & quotas without calling YouTube")
    p.add_argument("--force", action="store_true", help="Upload even if upload_receipt.json already exists or QA report missing")
    args = p.parse_args()

    secrets_p = Path(args.client_secrets).expanduser()
    token_p = Path(args.token).expanduser()

    if args.auth_only:
        yt = get_youtube_service(secrets_p, token_p)
        ch = yt.channels().list(part="snippet,statistics", mine=True).execute()
        items = ch.get("items", [])
        if not items:
            print("Authenticated, but no YouTube channel found on this Google account.")
        else:
            for item in items:
                sn = item.get("snippet", {})
                print(f"Authenticated Channel: {sn.get('title')} (id={item.get('id')})")
        return

    if not args.projects:
        p.error("Provide at least one project slug/path, or pass --auth-only")

    base_dt = None
    if args.publish_at:
        raw_dt = args.publish_at.replace("Z", "+00:00")
        base_dt = datetime.datetime.fromisoformat(raw_dt)

    plans = []
    skipped = []
    for idx, item in enumerate(args.projects):
        proj = resolve_project_dir(item)
        rec_p = proj / "upload_receipt.json"
        if rec_p.exists() and not args.force:
            rec = load_json(rec_p)
            skipped.append({"slug": proj.name, "reason": f"already uploaded ({rec.get('url')})"})
            continue
        pub_iso = None
        if base_dt is not None:
            dt = base_dt + datetime.timedelta(hours=idx * args.stagger_hours)
            pub_iso = dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        plans.append(build_payload(proj, args, pub_iso))

    if args.dry_run:
        summary = {
            "dry_run": True,
            "client_secrets_present": secrets_p.exists(),
            "token_present": token_p.exists(),
            "queued_count": len(plans),
            "skipped": skipped,
            "queued": [
                {
                    "slug": pl["slug"],
                    "mp4": str(pl["mp4"]),
                    "size_mb": pl["size_mb"],
                    "qa_score": pl["qa_score"],
                    "title": pl["body"]["snippet"]["title"],
                    "title_len": len(pl["body"]["snippet"]["title"]),
                    "tags_count": len(pl["body"]["snippet"]["tags"]),
                    "privacyStatus": pl["body"]["status"]["privacyStatus"],
                    "publishAt": pl["body"]["status"].get("publishAt"),
                    "containsSyntheticMedia": pl["body"]["status"].get("containsSyntheticMedia", False),
                }
                for pl in plans
            ],
        }
        print(json.dumps(summary, indent=2))
        return

    if not plans:
        print(json.dumps({"uploaded": [], "skipped": skipped}, indent=2))
        return

    yt = get_youtube_service(secrets_p, token_p)
    ch = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    ch_name = ch[0]["snippet"]["title"] if ch else "unknown"
    print(f"Uploading {len(plans)} Short(s) to YouTube channel: {ch_name}")

    results = []
    for i, pl in enumerate(plans):
        print(f"[{i + 1}/{len(plans)}] Uploading {pl['slug']} ({pl['size_mb']} MB)...")
        rec = upload_one(yt, pl, playlist_id=args.playlist_id)
        results.append(rec)
        print(f"  -> Uploaded: {rec['url']} ({rec['privacy_status']})")
        if i < len(plans) - 1:
            time.sleep(1.5)

    print(json.dumps({"channel": ch_name, "uploaded": results, "skipped": skipped}, indent=2))


if __name__ == "__main__":
    main()

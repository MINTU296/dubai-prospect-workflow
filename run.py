#!/usr/bin/env python3
"""Dubai-property prospect discovery for South India - one command, end to end.

    python run.py                    collect (cached) -> qualify -> export
    python run.py --offline          re-qualify from the local cache only, no network
    python run.py --refresh          ignore the cache and refetch everything
    python run.py --as-of 2026-11-11    reproduce a past run's freshness decisions
    python run.py --purge-cache      delete all cached public text and exit

Outputs (./output): prospects_all.csv, shortlist_top5.csv, prospects.xlsx, summary.md,
run_manifest.json

Exit codes: 0 success - 1 unexpected error - 2 bad configuration or arguments -
3 nothing collected (existing outputs are left untouched)
"""
import argparse
import logging
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import config
from prospector import cache, export, pipeline
from prospector.sources import youtube

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("prospector")


def load_env_file(path):
    """Read KEY=VALUE lines from a local .env file into the environment.

    A variable that is already set wins, blank values are skipped, and values are never
    logged. The file is optional and is ignored by git."""
    try:
        lines = Path(path).read_text(encoding="utf-8-sig").splitlines()      # tolerate a BOM from Windows editors
    except (OSError, UnicodeDecodeError):
        return 0
    n = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].strip()         # KEY=abc  # a note
        if name.isidentifier() and value and not os.environ.get(name):
            os.environ[name] = value
            n += 1
    return n


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true", help="use only the local cache; make no network calls")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache and refetch")
    ap.add_argument("--skip-youtube", action="store_true")
    ap.add_argument("--ai-read", action="store_true",
                    help="also have a Claude model read every commenter's comments (needs ANTHROPIC_API_KEY; optional)")
    ap.add_argument("--as-of", help="ISO date used for freshness decisions (default: today)")
    ap.add_argument("--out", default=str(ROOT / "output"), help="output directory")
    ap.add_argument("--cache-dir", default=str(ROOT / "data" / "cache"))
    ap.add_argument("--review-file", default=str(ROOT / "review" / "manual_review.csv"))
    ap.add_argument("--video-review-file", default=str(ROOT / "review" / "video_review.csv"))
    ap.add_argument("--env-file", default=str(ROOT / ".env"), help="file with YOUTUBE_API_KEY=... (default: .env)")
    ap.add_argument("--find", metavar="TEXT", help="list the prospect_id of everyone whose cached comment contains TEXT, then exit "
                    "(for adding someone to the review file; works offline)")
    ap.add_argument("--purge-cache", action="store_true", help="delete all cached public text and exit")
    ap.add_argument("--allow-empty", action="store_true", help="write outputs even if nothing was collected")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("-q", "--quiet", action="store_true")
    a = ap.parse_args(argv)
    if a.as_of:
        try:
            date.fromisoformat(a.as_of)
        except ValueError:
            ap.error("--as-of must be an ISO date, e.g. 2026-11-11")
    if a.offline and a.refresh:
        ap.error("--offline and --refresh cannot be combined")
    return a


def collect(a, cache_dir):
    """Run the collector. A failure is logged and reported in the funnel, never a crash."""
    signals, funnel, yt_key, yt_live = [], {}, "", False
    if not a.skip_youtube:
        log.info("[1/4] YouTube discovery (Data API v3)")
        # Key from the environment (or the local .env file). Hosted setups where a gateway injects the credential set
        # YOUTUBE_KEY_VIA_GATEWAY=1; otherwise no key means no call is made at all.
        key = os.environ.get("YOUTUBE_API_KEY", "").strip()
        if not key and os.environ.get("YOUTUBE_KEY_VIA_GATEWAY") == "1":
            key = "injected-by-gateway"
        live = not a.offline and bool(key) and youtube.key_works(key)
        yt_key, yt_live = key, live
        if not a.offline and not live:
            log.warning("no working YOUTUBE_API_KEY - YouTube, the main source, will use cached data only (see README)")
            funnel["youtube_note"] = "no working API key; cached data only"
        try:
            s, st = youtube.collect(key, cache_dir / "youtube", offline=not live, refresh=a.refresh and live)
            signals += s
            st.update({k: v for k, v in funnel.items() if k == "youtube_note" and "youtube_note" not in st})
            funnel.update(st)
        except Exception:
            log.exception("YouTube collection failed - continuing without it")
            funnel["youtube_error"] = "collector failed, see log"
    return signals, funnel, (yt_key, yt_live)


def find(a, cache_dir):
    """Print the prospect_id and current status of everyone whose cached comment contains a text.

    People who are not candidates are not in the sheet, so this is how a reviewer finds the id
    needed to add one of them to review/manual_review.csv. No handle is printed."""
    from prospector import qualify
    signals, _ = youtube.collect("", cache_dir / "youtube", offline=True)
    candidates, _, _ = pipeline.run(list(signals), overrides=export.load_overrides(a.review_file),
                                    video_notes=export.load_video_review(a.video_review_file), as_of=config.TODAY)
    status = {p["id"]: p["status"] for p in candidates}
    needle, shown = a.find.lower(), 0
    for s in signals:
        if needle in s["text"].lower():
            pid = qualify.prospect_id(s)
            print(f"{pid}  {status.get(pid, 'not a candidate'):17}  {s['date']}  {' '.join(s['text'].split())[:110]}")
            shown += 1
    print(f"{shown} comment(s) contain {a.find!r}")
    return 0


def make_reader(a, cache_dir):
    """The optional AI reader, or None (after logging why) if it cannot be set up."""
    from prospector import ai_reader
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    call = None
    if a.offline:
        log.info("AI reader: offline - cached readings only")
    elif not key:
        log.warning("AI reader: no ANTHROPIC_API_KEY (put it in .env) - cached readings only")
    else:
        try:
            call = ai_reader.anthropic_call(key)
        except ImportError:
            log.error("--ai-read needs the Anthropic SDK: pip install -r requirements-ai.txt")
            return None
    return ai_reader.Reader(call, cache_dir / "ai")


def main(argv=None):
    a = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.WARNING if a.quiet else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    load_env_file(a.env_file)
    cache_dir = Path(a.cache_dir)

    if a.purge_cache:
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        log.info("cache deleted: %s", cache_dir)
        return 0

    if a.as_of:
        config.TODAY = a.as_of
    problems = config.validate()
    if problems:
        for p in problems:
            log.error("config: %s", p)
        return 2

    # Data retention: cached public text older than the limit is deleted on every online run.
    if not a.offline:
        n = cache.purge(cache_dir, config.CACHE_RETENTION_DAYS)
        if n:
            log.info("retention: deleted %d cached responses older than %d days", n, config.CACHE_RETENTION_DAYS)

    if a.find:
        return find(a, cache_dir)

    signals, funnel, (yt_key, yt_live) = collect(a, cache_dir)
    if not signals and not a.allow_empty:
        log.error("nothing was collected (no cache, no network, or no API access) - existing outputs left untouched")
        return 3

    channel_country, extra_units = None, [0]
    if not a.skip_youtube and config.YOUTUBE_CHANNEL_COUNTRY:
        def channel_country(ids):
            found, units = youtube.channel_countries(yt_key, cache_dir / "youtube", ids, offline=not yt_live,
                                                     refresh=a.refresh and yt_live)
            extra_units[0] += units
            return found

    reader = None
    if a.ai_read:
        reader = make_reader(a, cache_dir)
        if reader is None:
            return 2

    log.info("[2/4] Qualifying %d public posts/comments", len(signals))
    overrides = export.load_overrides(a.review_file)
    candidates, shortlist, stats = pipeline.run(signals, overrides=overrides,
                                                channel_country=channel_country, reader=reader,
                                                video_notes=export.load_video_review(a.video_review_file), as_of=config.TODAY)
    funnel = {"raw_records_scanned": stats.pop("raw_records_scanned"), **funnel, **stats}
    if reader is not None:
        funnel.update(reader.stats)
    if "youtube_quota_units" in funnel:
        funnel["youtube_quota_units"] += extra_units[0]

    log.info("[3/4] Exporting to %s", a.out)
    export.write_all(candidates, shortlist, funnel, a.out, as_of=config.TODAY)

    log.info("[4/4] Done")
    for k, v in funnel.items():
        log.info("   %s: %s", k, f"{len(v)} entries (see summary.md)" if isinstance(v, list) else v)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.warning("interrupted - cached data is kept; re-run to resume")
        sys.exit(130)
    except Exception:
        log.exception("unexpected error")
        sys.exit(1)

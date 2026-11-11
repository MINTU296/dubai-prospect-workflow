"""YouTube comment discovery through the official YouTube Data API v3 (free key).

Finds videos about buying Dubai property aimed at South Indian audiences
(Tamil / Malayalam / Telugu / Kannada, or naming a South India city) and reads
their public comments.

Reliability properties:
- transient failures (network errors, 429, 5xx) are retried with backoff and NEVER cached;
- only successful answers and permanent conditions (comments disabled, video gone) are cached;
- cached answers expire (config.CACHE_TTL_HOURS); if the API then fails, the stale answer is used;
- running out of quota or an invalid key switches the client to cache-only instead of crashing;
- the API key is sent in a header, never in a URL, and never logged.
"""
import hashlib
import json
import logging
import re
import time
from pathlib import Path

import requests

import config
from prospector import cache
from prospector import lexicon as L
from prospector.textsig import _SOUTH_RE, clean_text, detect_script, find_location

log = logging.getLogger("prospector.youtube")

_DUBAI = re.compile(L.DUBAI, re.I)
_TOPIC = re.compile(L.PROPERTY + "|" + L.INVEST, re.I)
_QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", "userRateLimitExceeded"}
_KEY_REASONS = {"keyInvalid", "keyExpired", "accessNotConfigured", "ipRefererBlocked", "API_KEY_INVALID"}
_PERMANENT_REASONS = {"commentsDisabled", "videoNotFound", "forbidden", "channelNotFound"}


def _error_reason(resp):
    """Machine-readable reason from a Google API error body ('' if unknown)."""
    try:
        err = resp.json().get("error", {})
    except ValueError:
        return ""
    for e in err.get("errors") or []:
        if e.get("reason"):
            return e["reason"]
    for d in err.get("details") or []:
        if d.get("reason"):
            return d["reason"]
    return err.get("status", "") if "API key not valid" not in str(err.get("message", "")) else "keyInvalid"


class YouTube:
    def __init__(self, api_key, cache_dir, offline=False, refresh=False):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.key, self.offline, self.refresh = api_key, offline or not api_key, refresh
        self.session = requests.Session()
        self.units = self.cache_hits = self.failures = self.stale_served = 0
        self._failed_in_a_row = 0
        self.stopped = ""              # why network access was switched off mid-run, if it was

    def _stop(self, why):
        if not self.stopped:
            log.warning("youtube: %s - continuing with cached data only", why)
        self.stopped, self.offline = why, True

    def get(self, endpoint, params, cost):
        """Cached GET. Returns the response dict, or None if nothing is available."""
        key = hashlib.sha1((endpoint + json.dumps(params, sort_keys=True)).encode()).hexdigest()[:20]
        f = self.cache / f"{endpoint}_{key}.json"
        cached = None if self.refresh else cache.read_json(f)
        if not isinstance(cached, dict):
            cached = None
        if cached is not None and (self.offline or cache.is_fresh(f, config.CACHE_TTL_HOURS)):
            self.cache_hits += 1
            return cached

        def fallback():
            # with --refresh the cache was not consulted above; if the API cannot answer, an
            # older answer is still better than silently dropping the video
            stale = cached if cached is not None else cache.read_json(f)
            stale = stale if isinstance(stale, dict) else None
            if stale is not None:
                self.stale_served += 1
            return stale

        if self.offline:
            return fallback()
        if self.units + cost > config.YOUTUBE_QUOTA_BUDGET:
            self._stop("quota budget for this run reached")
            return fallback()
        for attempt in range(config.YOUTUBE_RETRIES):
            try:
                r = self.session.get(f"{config.YOUTUBE_API}/{endpoint}", params=params,
                                     headers={"X-Goog-Api-Key": self.key}, timeout=config.HTTP_TIMEOUT_SEC)
            except requests.RequestException as e:
                log.debug("youtube request failed (%s), attempt %d", type(e).__name__, attempt + 1)
                time.sleep(config.YOUTUBE_BACKOFF_SEC * (2 ** attempt))
                continue
            if r.status_code == 200:
                self.units += cost
                self._failed_in_a_row = 0
                try:
                    data = _strip_contacts(r.json())      # redact before anything touches disk
                except ValueError:
                    break
                cache.write_json_atomic(f, data)
                return data
            reason = _error_reason(r)
            if reason in _QUOTA_REASONS:
                self._stop("API quota exhausted")
                return fallback()
            if r.status_code in (400, 401, 403) and reason in _KEY_REASONS:
                self._stop("API key rejected (" + reason + ")")
                return fallback()
            if r.status_code == 404 or reason in _PERMANENT_REASONS:
                self.units += cost
                data = {"items": [], "_permanent_error": reason or str(r.status_code)}
                cache.write_json_atomic(f, data)          # e.g. comments disabled: no point retrying
                return data
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(config.YOUTUBE_BACKOFF_SEC * (2 ** attempt))
                continue
            log.debug("youtube %s -> HTTP %s (%s), not cached", endpoint, r.status_code, reason)
            break
        self.failures += 1
        self._failed_in_a_row += 1
        if self._failed_in_a_row >= config.YOUTUBE_MAX_CONSECUTIVE_FAILURES:
            self._stop("API unreachable (%d requests failed in a row)" % self._failed_in_a_row)   # circuit breaker
        return fallback()


_TEXT_KEYS = ("textOriginal", "textDisplay", "title", "description", "channelTitle", "authorDisplayName")


def _strip_contacts(data):
    """Normalise and redact every free-text field of an API response before it is cached:
    comment text, and also video titles, descriptions, channel names and tags (sellers put
    phone numbers in all of them). Fields that are not needed are dropped."""
    def clean(node):
        if isinstance(node, dict):
            had = False
            for k, v in list(node.items()):
                if k in _TEXT_KEYS and isinstance(v, str):
                    node[k], h = clean_text(v)
                    had = had or (h and k in ("textOriginal", "textDisplay"))
                elif k == "tags" and isinstance(v, list):
                    node[k] = [clean_text(t)[0] if isinstance(t, str) else t for t in v]
                elif k in ("authorProfileImageUrl", "authorChannelUrl"):
                    del node[k]                 # not needed; a channel URL can embed a phone-number handle
                else:
                    clean(v)
            if had:
                node["_had_contact"] = True
        elif isinstance(node, list):
            for item in node:
                clean(item)
    clean(data.get("items") if isinstance(data, dict) else None)
    return data


_LANG_WORDS = {"ta": r"\btamil\b|\bthamizh\b", "ml": r"\bmalayalam\b", "te": r"\btelugu\b", "kn": r"\bkannada\b"}
# creators also name the language inside a hashtag: #teluguindubai, #tamilshorts
_LANG_HASHTAG = {"ta": r"#\w*tamil\w*", "ml": r"#\w*malayalam\w*", "te": r"#\w*telugu\w*", "kn": r"#\w*kannada\w*"}
# A video is tied to a city only when it is about an event held there ("Dubai Property Show in Hyderabad").
_EVENT = r"(?:expo|show|exhibition|roadshow|summit|event)"
_EVENT_CITY = re.compile(rf"\b{_EVENT}\b[^|\n]{{0,40}}?\b(?:in|at)\s+(?P<a>{_SOUTH_RE.pattern})|(?P<b>{_SOUTH_RE.pattern})\s+(?:property\s+|real\s+estate\s+)?{_EVENT}\b", re.I)
_OFF_TOPIC = re.compile(r"home\s*tour|\bgold\b|బంగారం|தங்கம்|സ്വർണ|\bjobs?\b|vacanc|\brent\b|for\s+rent|bed\s*space|partition|"
                        r"cost\s+of\s+living|become\s+a\s+real\s+estate\s+agent|\bvlog\b|dubai[\s-]+style", re.I)


def _video_language(sn):
    """Regional language of a video from its own metadata - never from the search query."""
    title = sn.get("title", "")
    lang = detect_script(title) or detect_script(sn.get("channelTitle", ""))
    if not lang and (sn.get("defaultAudioLanguage") or "")[:2] in L.LANG_STATE:
        lang = sn["defaultAudioLanguage"][:2]
    if not lang:
        blob = (title + " " + " ".join(sn.get("tags") or [])).lower()
        lang = (next((k for k, rx in _LANG_WORDS.items() if re.search(rx, blob)), "")
                or next((k for k, rx in _LANG_HASHTAG.items() if re.search(rx, blob)), ""))
    return lang


def _video_meta(item):
    sn = item.get("snippet") or {}
    raw_title = sn.get("title", "")
    ev = _EVENT_CITY.search(raw_title)
    loc = find_location(ev.group("a") or ev.group("b")) if ev else {"city": "", "state": ""}
    try:
        n_comments = int((item.get("statistics") or {}).get("commentCount", 0) or 0)
    except (TypeError, ValueError):
        n_comments = 0
    return {
        "id": item["id"], "title": clean_text(raw_title)[0],      # titles often carry a phone number
        "channel_id": sn.get("channelId"), "channel": sn.get("channelTitle", ""),
        "published": sn.get("publishedAt", "")[:10], "comments": n_comments,
        "lang": _video_language(sn), "city": loc["city"], "state": loc["state"],
        # the TITLE must be about Dubai property/investing, and not a home tour, gold, job or rental video
        "relevant": bool(_DUBAI.search(raw_title) and _TOPIC.search(raw_title) and not _OFF_TOPIC.search(raw_title)),
    }


def _signal(c, cid, video, is_reply, parent_author=None):
    """Normalised record for one comment, or None if it cannot be attributed or dated.

    parent_author is the channel id of the top-level comment a reply sits under; it tells a reply
    to the video's creator (still an enquiry) from a reply to another viewer (discussion)."""
    if not isinstance(c, dict) or not cid:
        return None
    author_id = (c.get("authorChannelId") or {}).get("value")
    published = (c.get("publishedAt") or "")[:10]
    if not author_id or len(published) != 10 or published < config.SIGNAL_AFTER:
        return None
    text, had_contact = clean_text(c.get("textOriginal") or c.get("textDisplay") or "")
    return {
        "platform": "youtube", "kind": "reply" if is_reply else "comment", "id": cid, "post_id": video["id"],
        "author_id": author_id, "author_name": clean_text(c.get("authorDisplayName") or "")[0],
        "text": text, "had_contact": had_contact or bool(c.get("_had_contact")),
        "url": f"https://www.youtube.com/watch?v={video['id']}&lc={cid}",
        "date": published,
        "context": f"YouTube: {video['channel']}", "context_title": video["title"],
        "context_city": video["city"], "context_state": video["state"], "context_lang": video["lang"],
        "context_is_property": True,   # only Dubai-property videos are read
        "is_owner": author_id == video["channel_id"],
        "reply_to": ("" if not is_reply or not parent_author else "creator" if parent_author == video["channel_id"]
                     else "self" if parent_author == author_id else "viewer"),
    }


def key_works(api_key):
    """One 1-unit call to check the key (or a gateway-injected credential) is accepted."""
    if not api_key:
        return False
    try:
        r = requests.get(f"{config.YOUTUBE_API}/videos", params={"part": "id", "id": "jNQXAC9IVRw"},
                         headers={"X-Goog-Api-Key": api_key}, timeout=20)
        return r.status_code == 200
    except requests.RequestException:
        return False


def channel_countries(api_key, cache_dir, channel_ids, offline=False, refresh=False):
    """Public country code declared on each channel: ({channel_id: "AE"}, quota_units_used).

    Channels that declare no country are left out. Only the id and the country code are asked
    for (a partial response), so nothing else about a commenter's channel is fetched or cached.
    Answers are kept per channel in one small file, so an offline re-run gives the same result
    whichever candidates it asks about; entries past the retention limit are dropped."""
    yt = YouTube(api_key, cache_dir, offline, refresh)
    path = Path(cache_dir) / "channel_country_map.json"
    now, stored = time.time(), cache.read_json(path)
    known = {k: v for k, v in (stored if isinstance(stored, dict) else {}).items()
             if isinstance(v, dict) and isinstance(v.get("t"), (int, float)) and isinstance(v.get("c"), str)
             and now - v["t"] < config.CACHE_RETENTION_DAYS * 86400}
    ids = sorted({i for i in channel_ids if isinstance(i, str) and i})
    ttl = None if config.CACHE_TTL_HOURS is None else config.CACHE_TTL_HOURS * 3600
    need = [i for i in ids if refresh or i not in known or (ttl is not None and now - known[i]["t"] >= ttl)]
    changed = False
    if not yt.offline:
        for k in range(0, len(need), 50):
            batch = need[k:k + 50]
            data = yt.get("channels", {"part": "snippet", "id": ",".join(batch), "maxResults": 50,
                                       "fields": "items(id,snippet/country)"}, cost=1)
            if not isinstance(data, dict) or data.get("_permanent_error"):
                continue                                   # keep whatever older answer there is
            got = {it.get("id"): ((it.get("snippet") or {}).get("country") or "")
                   for it in data.get("items") or [] if isinstance(it, dict)}
            for i in batch:
                c = got.get(i, "")
                known[i] = {"c": c.upper() if isinstance(c, str) else "", "t": now}
            changed = True
    if changed or (isinstance(stored, dict) and len(known) != len(stored)):
        cache.write_json_atomic(path, known)
    return {i: known[i]["c"] for i in ids if i in known and known[i]["c"]}, yt.units


def _threads(data):
    """(comment_snippet, comment_id, is_reply, parent_author_id) for every comment in a commentThreads response."""
    for th in (data or {}).get("items") or []:
        top = ((th or {}).get("snippet") or {}).get("topLevelComment") or {}
        parent = None
        if isinstance(top.get("snippet"), dict):
            parent = (top["snippet"].get("authorChannelId") or {}).get("value")
            yield top["snippet"], top.get("id"), False, None
        for rep in ((th or {}).get("replies") or {}).get("comments") or []:
            if isinstance(rep, dict) and isinstance(rep.get("snippet"), dict):
                yield rep["snippet"], rep.get("id"), True, parent


def collect(api_key, cache_dir, offline=False, refresh=False):
    """Returns (signals, stats)."""
    yt = YouTube(api_key, cache_dir, offline, refresh)
    videos, signals, seen = {}, [], set()

    def add(snippet, cid, video, is_reply, parent=None):
        sig = _signal(snippet, cid, video, is_reply, parent)
        if sig and cid not in seen:
            seen.add(cid)
            signals.append(sig)
            return True
        return False

    ids = set()
    for query in config.YOUTUBE_QUERIES:
        data = yt.get("search", {"part": "id", "q": query, "type": "video", "regionCode": "IN",
                                 "maxResults": config.YOUTUBE_RESULTS_PER_QUERY, "order": "relevance",
                                 "publishedAfter": config.SIGNAL_AFTER + "T00:00:00Z"}, cost=100)
        for it in (data or {}).get("items") or []:
            vid = ((it or {}).get("id") or {}).get("videoId")
            if vid:
                ids.add(vid)
    ids = sorted(ids)
    for i in range(0, len(ids), 50):
        data = yt.get("videos", {"part": "snippet,statistics", "id": ",".join(ids[i:i + 50])}, cost=1)
        for it in (data or {}).get("items") or []:
            if isinstance(it, dict) and it.get("id"):
                videos[it["id"]] = _video_meta(it)

    # A video whose own metadata names no language takes the language its channel's other videos
    # share (at least two of them, all the same language): a Telugu realtor's English-titled clip.
    by_channel = {}
    for v in videos.values():
        if v["lang"]:
            by_channel.setdefault(v["channel_id"], []).append(v["lang"])
    for v in videos.values():
        langs = by_channel.get(v["channel_id"]) or []
        if not v["lang"] and len(langs) >= 2 and len(set(langs)) == 1:
            v["lang"], v["lang_from_channel"] = langs[0], True

    # 1. regional videos: read the comment threads
    chosen = sorted((v for v in videos.values() if v["relevant"] and v["comments"] >= config.YOUTUBE_MIN_COMMENTS
                     and (v["lang"] or v["state"])),      # must have some South India link
                    key=lambda v: (-v["comments"], v["id"]))[:config.YOUTUBE_MAX_VIDEOS]
    log.info("youtube: %d videos found, %d relevant Dubai-property videos with a South India link", len(videos), len(chosen))
    truncated = 0
    for v in chosen:
        token = None
        for _ in range(config.YOUTUBE_COMMENT_PAGES):
            p = {"part": "snippet,replies", "videoId": v["id"], "maxResults": 100, "order": "time",
                 "textFormat": "plainText"}
            if token:
                p["pageToken"] = token
            data = yt.get("commentThreads", p, cost=1) or {}
            for snippet, cid, is_reply, parent in _threads(data):
                add(snippet, cid, v, is_reply, parent)
            token = data.get("nextPageToken")
            if not token:
                break
        truncated += bool(token)           # more threads exist than the page limit allows

    # 2. anchor search on the most-commented relevant videos, whatever their language
    anchor_videos = sorted((v for v in videos.values() if v["relevant"] and v["comments"] >= config.YOUTUBE_ANCHOR_MIN_COMMENTS),
                           key=lambda v: (-v["comments"], v["id"]))[:config.YOUTUBE_ANCHOR_VIDEOS]
    n_anchor = 0
    for v in anchor_videos:
        for term in config.YOUTUBE_ANCHOR_TERMS:
            data = yt.get("commentThreads", {"part": "snippet", "videoId": v["id"], "maxResults": 100,
                                             "searchTerms": term, "textFormat": "plainText"}, cost=1)
            for snippet, cid, is_reply, parent in _threads(data):
                n_anchor += add(snippet, cid, v, is_reply, parent)
    log.info("youtube: anchor search on %d videos found %d more comments naming a South India place", len(anchor_videos), n_anchor)

    stats = {"youtube_quota_units": yt.units, "youtube_cache_hits": yt.cache_hits,
             "youtube_videos_found": len(videos), "youtube_videos_read_in_full_or_part": len(chosen),
             "youtube_videos_with_more_comments_than_the_page_limit": truncated, "youtube_rows": len(signals)}
    if yt.stopped:
        stats["youtube_note"] = yt.stopped + " - used cached data for the rest"
    if yt.failures:
        stats["youtube_failed_requests"] = yt.failures
    if yt.stale_served:
        stats["youtube_stale_answers_used"] = yt.stale_served
    return signals, stats

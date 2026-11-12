"""The qualification pipeline: raw signals in, classified candidates out.

Pure and deterministic: the same signals, overrides and as-of date always give the
same sheet, whatever order the signals arrive in. The only side effects are the
optional `enrich` and `channel_country` callbacks (public lookups), which the caller supplies.
"""
import hashlib
import logging
from collections import Counter
from datetime import date

import config
from prospector import qualify

log = logging.getLogger("prospector.pipeline")

STATUSES = ("strong_signal", "needs_validation", "reject")
OVERRIDE_STATUSES = STATUSES + ("exclude",)       # exclude = remove the person from all outputs
_ORDER = {"strong_signal": 0, "needs_validation": 1, "reject": 2}


def valid_signal(s):
    """A record the pipeline can attribute, date and link back to its source."""
    if not isinstance(s, dict):
        return False
    if not all(isinstance(s.get(k), str) and s.get(k) for k in ("platform", "author_id", "url", "date", "context")):
        return False
    if not isinstance(s.get("text"), str):
        return False
    try:
        date.fromisoformat(s["date"])
    except ValueError:
        return False
    return True


def _assign_ids(prospects):
    """Stable public ids; a (very unlikely) hash collision is resolved, never silently merged."""
    seen = {}
    for p in prospects:
        pid = qualify.prospect_id(p)
        owner = (p["platform"], p["author_id"])
        if seen.get(pid, owner) != owner:
            pid = p["platform"][:2].upper() + "-" + hashlib.sha1(str(p["author_id"]).encode()).hexdigest()[:16]
            log.warning("prospect id collision resolved for %s", pid)
        seen[pid] = owner
        p["id"] = pid


def run(signals, *, overrides=None, enrich=None, channel_country=None, reader=None, video_notes=None, as_of=None, cap=None):
    """Returns (candidates, shortlist, funnel).

    signals   - list of normalised records from the collectors
    overrides - {prospect_id: {"status": ..., "note": ...}} manual review decisions
    enrich    - optional callable(prospect) -> (south_activity, other_activity)
    channel_country - optional callable([youtube channel ids]) -> {channel_id: country code}
    reader    - optional callable([prospects]) -> {prospect_id: verified AI label} (ai_reader.Reader)
    video_notes - {video_id: note} for videos a reviewer found are not about Dubai property
    as_of     - ISO date used for freshness (default: today)
    cap       - optional maximum rows in the sheet (default: config.CANDIDATE_CAP; None = all)
    """
    as_of = as_of or config.TODAY
    cap = config.CANDIDATE_CAP if cap is None else cap
    overrides = overrides or {}
    funnel = {"raw_records_scanned": len(signals)}

    # 1. validate + drop the same record collected twice; fix the processing order
    good, seen = [], set()
    for s in signals:
        key = (s.get("platform"), s.get("id")) if isinstance(s, dict) else None
        if valid_signal(s) and (s.get("id") is None or key not in seen):
            seen.add(key)
            good.append(s)
    funnel["invalid_or_repeated_records_dropped"] = len(signals) - len(good)
    good.sort(key=lambda s: (s["platform"], s["author_id"], s["date"], str(s.get("id"))))

    # 2. assess every record
    video_notes = video_notes or {}
    for s in good:
        if s.get("post_id") in video_notes:
            s["off_target"] = video_notes[s["post_id"]]
        qualify.assess(s)
    in_scope = [s for s in good if s["in_scope"]]
    funnel["unique_commenters"] = len({(s["platform"], s["author_id"]) for s in good})
    funnel["records_in_a_dubai_property_context"] = len(in_scope)

    # 3. dedupe into one prospect per author
    scoped_authors = {(s["platform"], s["author_id"]) for s in in_scope}
    groups, dupes = qualify.group_by_author([s for s in good if (s["platform"], s["author_id"]) in scoped_authors])
    prospects = [qualify.build_prospect(g) for _, g in sorted(groups.items())]
    _assign_ids(prospects)
    funnel["duplicate_records_collapsed"] = dupes
    funnel["unique_authors_about_dubai_property"] = len(prospects)
    funnel["records_merged_into_existing_author"] = sum(len(g) - 1 for g in groups.values())

    # 3b. optional AI reading of every commenter (never of a video's own creator)
    if reader is not None:
        try:
            labels = reader([p for p in prospects if not p["is_owner"]]) or {}
        except Exception:
            log.exception("AI reader failed - continuing with the keyword rules alone")
            labels = {}
        for p in prospects:
            if p["id"] in labels and not p["is_owner"]:
                qualify.apply_reading(p, labels[p["id"]])
        funnel["commenters_read_by_ai"] = len(labels)
        funnel["buying_intent_found_only_by_ai"] = sum(1 for p in prospects if "read_by_ai" in p["markers"])

    # 4. enrich location for authors with intent but no stated location
    if enrich is not None:
        todo = [p for p in prospects if p["platform"] == "reddit" and p["tier"] in ("strong", "medium")
                and not p["any_agent"] and not p["abroad"] and p["loc"]["tier"] in ("", "mention")]
        todo.sort(key=lambda p: (-qualify.TIER_RANK[p["tier"]], -p["score"], p["id"]))
        todo, done = todo[:config.ENRICH_MAX_AUTHORS], 0
        log.info("looking up public subreddit activity for %d authors", len(todo))
        for p in todo:
            p["activity_south"], p["activity_other"], p["activity_dubai"] = enrich(p)
            done += p["activity_south"] is not None
            qualify.resolve_location(p)
        funnel["authors_checked_for_south_india_activity"] = f"{done} of {len(todo)}"

    # 4b. country a YouTube candidate's channel publicly declares (most declare none)
    if channel_country is not None:
        todo = sorted({p["author_id"] for p in prospects if p["platform"] == "youtube" and not p["is_owner"]
                       and (p["tier"] or p["any_agent"] or p["id"] in overrides)})
        try:
            found = channel_country(todo) or {}
        except Exception:
            log.exception("channel country lookup failed - continuing without it")
            found = {}
        for p in prospects:
            if p["platform"] == "youtube":
                p["channel_country"] = found.get(p["author_id"], "")
        funnel["candidate_channels_declaring_a_country"] = f"{sum(1 for i in todo if found.get(i))} of {len(todo)}"
        funnel["candidate_channels_declaring_a_country_outside_india"] = sum(1 for i in todo if found.get(i, "IN") != "IN")

    # 5. classify, then apply manual review decisions
    applied, used, unsupported, refused = 0, set(), [], []
    for p in prospects:
        o = overrides.get(p["id"])
        upgrade = bool(o) and o["status"] in ("strong_signal", "needs_validation")
        if upgrade:
            used.add(p["id"])
            # A decision in someone's favour must say what was read and quote it, and the quote must
            # be in the person's comments. Otherwise it cannot be checked, so it is not applied.
            if not (o.get("signal") and o.get("quote") and qualify.apply_review_signal(p, o["signal"], o["quote"])):
                unsupported.append(p["id"])
                o = None
        p["status"], p["reason"], p["unverified"] = qualify.classify(p, as_of)
        p["review"] = "automatic"
        if o and upgrade and (p["is_owner"] or p["any_agent"]):
            refused.append(p["id"])            # no decision makes a seller or a video's creator a prospect
            o = None
        if o:
            used.add(p["id"])
            if o["status"] != p["status"]:
                p["reason"] = f"[Manual review] {o['note']} (automatic rule said: {p['status']})"
            elif o["status"] == "reject":
                p["reason"] = f"[Manual review] {o['note']}"       # same status, but the reviewer's reason is the accurate one
            p["status"], p["review"] = o["status"], "manual: " + o["note"]
            applied += 1
    funnel["manual_review_decisions_applied"] = applied
    if refused:
        funnel["manual_review_upgrades_refused_seller_or_creator"] = sorted(refused)
    if unsupported:
        funnel["manual_review_quotes_not_found"] = sorted(unsupported)
        log.warning("%d manual review decision(s) not applied: the quote is not in that person's comments", len(unsupported))
    in_run = {p["platform"][:2].upper() for p in prospects}       # ignore decisions about a source this run did not read
    stale = sorted(i for i in set(overrides) - used if i[:2] in in_run)
    if stale:
        funnel["manual_review_ids_not_found_in_this_run"] = stale
        log.warning("%d manual review id(s) did not match any prospect in this run", len(stale))
    excluded = [p for p in prospects if p["status"] == "exclude"]
    if excluded:
        funnel["excluded_on_request"] = len(excluded)
    prospects = [p for p in prospects if p["status"] != "exclude"]

    # 6. A candidate is someone who asked or said something a seller could act on: a wish to
    #    buy, a buying question, a budget, a request for price/details/contact - or a seller.
    #    A video's own creator is never a discovered prospect, and people who only mention
    #    the topic are noise. Both are counted and removed.
    creators = [p for p in prospects if p["is_owner"]]
    funnel["video_creators_removed"] = len(creators)
    prospects = [p for p in prospects if not p["is_owner"]]
    # ... and so is anyone a reviewer qualified by hand, even where no keyword rule matched.
    candidates = [p for p in prospects if p["tier"] or p["any_agent"]
                  or (p["review"] != "automatic" and p["status"] in ("strong_signal", "needs_validation"))]
    funnel["irrelevant_authors_removed_no_signal"] = len(prospects) - len(candidates)
    candidates.sort(key=lambda p: p["id"])
    candidates.sort(key=lambda p: p["best"]["date"], reverse=True)      # stable: ties stay in id order
    funnel["candidates_discovered"] = len(candidates)
    if video_notes:
        funnel["candidates_under_videos_not_about_dubai"] = sum(1 for p in candidates if p.get("off_target"))
    counts = Counter(p["status"] for p in candidates)
    for k in STATUSES:
        funnel[k] = counts.get(k, 0)                 # counted over ALL candidates
    funnel["strong_plus_needs_validation"] = funnel["strong_signal"] + funnel["needs_validation"]
    # the honest answer to "how many genuinely qualify": intent in their own words AND a home they state
    funnel["meet_both_tests_in_their_own_words"] = sum(
        1 for p in candidates if qualify.meets_both(p))
    if cap is not None:
        # An optional sheet limit never drops a qualified prospect: only the oldest rejects go.
        qualified = [p for p in candidates if p["status"] != "reject"]
        rejects = [p for p in candidates if p["status"] == "reject"][:max(0, cap - len(qualified))]
        funnel["rejects_not_shown_oldest_first_to_go"] = len(candidates) - len(qualified) - len(rejects)
        candidates = qualified + rejects
    funnel["candidates_in_sheet"] = len(candidates)

    candidates.sort(key=lambda p: (_ORDER[p["status"]], -qualify.rank_key(p, as_of), p["id"]))
    # Shortlist = up to five non-rejected prospects in rank order: strong signals first, then
    # the best needs_validation records, each keeping its label.
    shortlist = [p for p in candidates if p["status"] != "reject"][:5]
    return candidates, shortlist, funnel

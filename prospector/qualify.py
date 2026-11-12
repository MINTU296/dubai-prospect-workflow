"""Turn raw signals (posts/comments) into de-duplicated, classified prospects.

Pipeline:  assess each signal -> group by author (dedupe) -> location evidence
           -> classify strong_signal / needs_validation / reject with reasons.
"""
import hashlib
import re
from collections import defaultdict
from datetime import date

import config
from prospector import lexicon as L
from prospector import textsig as T

TIER_RANK = {"strong": 3, "medium": 2, "weak": 1, "": 0}
LOC_RANK = {"explicit": 4, "community": 3, "mention": 2, "context": 1, "language": 1, "": 0}

_DUBAI = re.compile(L.DUBAI, re.I)
_PROP = re.compile(L.PROPERTY, re.I)
_INVEST = re.compile(L.INVEST, re.I)
_SOUTH_ALT = T._SOUTH_RE.pattern
_ASSET = r"(?:propert(?:y|ies)|flats?|apartments?|villas?|plots?|land|house|home|real\s*estate|site|bhk)"
_TARGET_DUBAI = re.compile(
    rf"\b(?:buy|buying|bought|invest|investing|investment|purchase|purchasing|own|{_ASSET})\s+(?:\w+\s+){{0,5}}?(?:in|at)\s+(?:the\s+)?(?:dubai|uae)\b"
    rf"|\b(?:dubai|uae)(?:'s)?\s+(?:\w+\s+){{0,2}}?(?:{_ASSET}|market|off[\s-]?plan|developers?|golden\s+visa)\b"
    rf"|{L.DUBAI_AREAS}|துபாய்|ദുബായ്|ദുബൈ|దుబాయ్|ದುಬೈ", re.I)
_BUY_IN_DUBAI = re.compile(
    r"\b(?:buy|buying|invest|investing|purchase|purchasing|own|owning|looking)\s+(?:\w+\s+){0,6}?(?:in|at)\s+(?:the\s+)?(?:dubai|uae)\b"
    rf"|\b(?:buy|buying|purchase|purchasing|invest\s+in|investing\s+in)\s+(?:\w+\s+){{0,3}}?(?:dubai|uae)\s+(?:\w+\s+){{0,2}}?{_ASSET}", re.I)
_DUBAI_AREA = re.compile(L.DUBAI_AREAS, re.I)
_TARGET_INDIA = re.compile(
    rf"\b(?:buy|buying|invest|investing|purchase|purchasing|{_ASSET})\s+(?:\w+\s+){{0,4}}?(?:in|at|near)\s+(?:the\s+)?(?:india\b|{_SOUTH_ALT}|{T._OTHER_IN_RE.pattern})", re.I)


def _focus(sig):
    """The part of the text that is about Dubai.

    If the thread/video itself is about Dubai property the whole text counts;
    otherwise only +-320 characters around each Dubai mention, so that a
    'buying a flat in Bangalore' post that mentions Dubai in passing is not
    read as Dubai buying intent.
    """
    text = sig["text"]
    if sig["thread_is_dubai_property"] or len(text) < 500:
        return text        # never the thread/video title: markers must come from the author's own words
    spans = [(max(0, m.start() - 320), m.end() + 320) for m in _DUBAI.finditer(text)]
    return " … ".join(text[a:b] for a, b in spans[:4]) if spans else ""


def assess(sig):
    """Annotate one signal in place with scope, markers, intent tier, location."""
    title = sig.get("context_title") or ""
    sig["thread_is_dubai_property"] = bool(sig.get("context_is_property") or T.is_dubai_property(title))
    focus = _focus(sig)
    # in scope = Dubai AND a property term close together (or the whole thread is about Dubai property)
    sig["in_scope"] = sig["thread_is_dubai_property"] or bool(
        _PROP.search(focus) and (_DUBAI.search(focus) or sig["context"].replace("r/", "") in config.DUBAI_SUBS))
    mk = T.markers(focus) if sig["in_scope"] else set()
    if sig["platform"] == "youtube":
        text = sig["text"].lstrip("\u200b\u200c\u200d\ufeff ")
        # A long comment under a property video must itself talk about property; short ones
        # ("interested, details please") inherit the video's topic.
        on_topic = bool(_PROP.search(text) or _INVEST.search(text) or mk & {"requirement", "budget"})
        if len(text) > 90 and not on_topic:
            sig["in_scope"], mk = False, set()
        if not on_topic:
            mk.discard("comparison")       # "Russia is better than Dubai" is not a property comparison
        mention = re.match(r"@([\w.\-]+)", text)
        if mention:
            # a reply to another commenter is discussion; a reply to the video's creator is still an enquiry
            squash = lambda v: re.sub(r"[^a-z0-9]", "", v.lower())
            who, creator = squash(mention.group(1)), squash(sig["context"].replace("YouTube:", ""))
            if not (who and creator and (who in creator or creator in who)):
                mk.add("reply_to_other")
        elif sig.get("reply_to") == "viewer":
            mk.add("reply_to_other")       # a reply under another viewer's comment, with no @mention
    # direction of the purchase: Dubai (wanted) vs India (not a Dubai buyer)
    if _TARGET_DUBAI.search(focus) or (sig["thread_is_dubai_property"] and sig["platform"] == "youtube"
                                       and not sig.get("off_target")):
        mk.add("target_dubai")
    if _TARGET_INDIA.search(focus):
        mk.add("target_india")
    if _BUY_IN_DUBAI.search(focus):
        mk.add("buy_in_dubai")
    if _DUBAI_AREA.search(focus):
        mk.add("dubai_area")           # names a Dubai community or developer
    sig["markers"] = mk
    sig["tier"], sig["score"] = T.intent_tier(mk)
    sig["loc"] = T.find_location(sig["text"] + "\n" + (title if sig["platform"] == "reddit" and sig["kind"] == "post" else ""))
    sig["script"] = T.detect_script(sig["text"])
    sig["focus"] = focus
    return sig


def _quote(sig, n=300):
    text = re.sub(r"\s+", " ", sig["focus"] or sig["text"]).strip()
    m = _DUBAI.search(text)
    start = max(0, (m.start() if m else 0) - 120)
    if len(text) <= n:
        start = 0
    q = text[start:start + n]
    return ("…" if start else "") + q + ("…" if start + n < len(text) else "")


def group_by_author(signals):
    """Deduplicate: one prospect per (platform, author). Exact repeat texts are collapsed."""
    groups, dupes = defaultdict(list), 0
    seen = set()
    for s in signals:
        key = (s["platform"], s["author_id"], re.sub(r"\W+", "", s["text"].lower())[:200])
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        groups[(s["platform"], s["author_id"])].append(s)
    return groups, dupes


_ADDITIVE = {"purchase_intent", "budget", "requirement", "timeline", "comparison", "process_question", "buying_question", "owner_investor"}


def build_prospect(sigs):
    """Aggregate one author's signals.

    Classification rests on the author's best post/comment, plus anything else they wrote
    under the SAME video or thread (a budget in one comment and "how do I buy" in the next
    belong together). Comments on different videos are never combined.
    """
    scoped = [s for s in sigs if s["in_scope"]]
    pool = scoped or sigs
    best = max(pool, key=lambda s: (TIER_RANK[s["tier"]], s["score"], "NEG_agent" in s["markers"], s["date"], str(s.get("id"))))
    markers, also = set(best["markers"]), []
    for s in scoped:
        if s is not best and s.get("post_id") and s.get("post_id") == best.get("post_id"):
            extra = (s["markers"] & _ADDITIVE) - markers
            if extra:
                markers |= extra
                also.append(s)
    tier, score = T.intent_tier(markers)
    p = {
        "platform": best["platform"], "author_id": best["author_id"], "name": best["author_name"],
        "best": best, "also": also, "signals": sigs, "n_signals": len(scoped),
        "markers": markers, "tier": tier, "score": score,
        "any_agent": any("NEG_agent" in s["markers"] for s in scoped) or T.is_business_name(best["author_name"]),
        "agent_by_name": not any("NEG_agent" in s["markers"] for s in scoped) and T.is_business_name(best["author_name"]),
        "is_owner": any(s.get("is_owner") for s in sigs),
        "had_contact": any(s.get("had_contact") for s in sigs),
        "activity_south": None, "activity_other": None, "activity_dubai": 0,
        "channel_country": "",          # country code the channel publicly declares, if looked up
        "read": None,                   # the optional AI reader's verified label for this person
        "off_target": best.get("off_target") or "",   # why the video is not about Dubai property, if so
    }
    resolve_location(p)
    return p


READ_MARKER = {"wants_to_buy": "purchase_intent", "buying_question": "buying_question", "already_bought": "owner_investor"}


def apply_reading(p, label):
    """Fold the AI reader's verified label into a prospect.

    The reader can add intent the keyword rules did not find (marked `read_by_ai`, so the row can
    reach needs_validation at most). It never removes or rejects anything: a disagreement, or a
    reading that the person states a home outside South India, becomes a flag in classify()."""
    p["read"] = label
    marker = READ_MARKER.get(label.get("intent"))
    # Only a high-confidence reading adds intent. In the first live run the medium-confidence
    # additions were mostly vague or off-target on a strict read.
    if marker and label.get("confidence") == "high" and not (p["markers"] & T.OWN_WORDS):
        p["markers"] = set(p["markers"]) | {marker, "read_by_ai"}
        p["tier"], p["score"] = T.intent_tier(p["markers"])
    if (label.get("home") and label.get("home_in_south_india") is False
            and label.get("confidence") in ("high", "medium") and not p["abroad"] and not p["other_india"]):
        p["read_home_elsewhere"] = label["home"]


REVIEW_SPECIFICS = ("budget", "timeline", "comparison", "requirement")


def valid_review_signal(signal):
    """'wants_to_buy', or with specifics the reviewer read: 'wants_to_buy+timeline+budget'."""
    parts = [x.strip() for x in (signal or "").split("+")]
    return bool(parts[0] in READ_MARKER and all(x in REVIEW_SPECIFICS for x in parts[1:]))


def apply_review_signal(p, signal, quote=""):
    """Record what a reviewer read in a comment no keyword rule matched (marked `found_on_review`).

    If the reviewer gave a quote it must be an exact substring of one of the person's comments;
    that comment then becomes the evidence shown. Returns False, changing nothing, if it is not."""
    if not valid_review_signal(signal):
        return False
    if quote:
        source = next((s for s in p["signals"] if quote in s["text"]), None)
        if source is None:
            return False
        p["best"], p["review_quote"] = source, quote
    parts = [x.strip() for x in signal.split("+")]
    if not (p["markers"] & T.OWN_WORDS):
        p["markers"] = set(p["markers"]) | {READ_MARKER[parts[0]], "found_on_review"} | set(parts[1:])
        p["tier"], p["score"] = T.intent_tier(p["markers"])
    return True


def read_summary(p):
    """One cell describing what the AI reader saw ('' when the stage did not run)."""
    r = p.get("read")
    if not r:
        return ""
    parts = [r["intent"].replace("_", " ") + (" (" + r["confidence"] + " confidence)" if r.get("confidence") else "")]
    if r.get("intent_quote"):
        parts.append('quote: "' + r["intent_quote"][:160] + '"')
    if r.get("home"):
        parts.append("says home is " + r["home"])
    if r.get("gloss"):
        parts.append("English (machine translation): " + r["gloss"])
    return " | ".join(parts)


def resolve_location(p):
    """Best available South India evidence, strongest tier first."""
    sigs, best = p["signals"], p["best"]
    loc = {"tier": "", "city": "", "state": "", "evidence": ""}

    def take(tier, city, state, evidence):
        better = LOC_RANK[tier] > LOC_RANK[loc["tier"]] or (LOC_RANK[tier] == LOC_RANK[loc["tier"]] and city and not loc["city"])
        if better:
            loc.update(tier=tier, city=city, state=state, evidence=evidence)

    for s in sorted(sigs, key=lambda s: s is not best):
        l = s["loc"]
        if l["tier"]:
            label = "self-stated" if l["tier"] == "explicit" else "place named in text"
            take(l["tier"], l["city"], l["state"], f'{label}: "{l["quote"]}" ({s["url"]})')
        if s.get("context_state") and s["platform"] == "reddit":
            take("community", s["context_city"], s["context_state"], f'posted in {s["context"]} ({s["url"]})')
        elif s.get("context_state"):
            take("context", s["context_city"], s["context_state"], f'commented on a video about an event in {s["context_city"] or s["context_state"]}: "{s["context_title"][:80]}" (context only - weak)')
        lang = s.get("script") or s.get("context_lang")
        if lang in L.LANG_STATE:
            how = "comment written in" if s.get("script") else "commented on a video in"
            take("language", "", L.LANG_STATE[lang], f"{how} {L.LANG_NAME[lang]} (language only - weak)")
    # Activity elsewhere that clearly outweighs the South India activity cancels it:
    # 10 items in r/bangalore against 350 in r/delhi is a Delhi resident.
    p["activity_conflict"] = ""
    south_n = max((p.get("activity_south") or {}).values(), default=0)
    other = p.get("activity_other") or {}
    if other and max(other.values()) >= 3 * max(south_n, 1):
        top_other = max(other, key=other.get)
        p["activity_conflict"] = f"{top_other} ({other[top_other]} items) vs South India communities ({south_n})"
    if p.get("activity_south") and not p["activity_conflict"]:
        subs = p["activity_south"]
        top = max(subs, key=subs.get)
        city, state = config.SOUTH_SUBREDDITS[top]
        ev = "public activity in " + ", ".join(f"r/{k} ({v} items)" for k, v in sorted(subs.items(), key=lambda kv: -kv[1]))
        if loc["tier"] in ("explicit", "community"):
            loc["evidence"] += "; also " + ev
        else:
            take("community", city, state, ev)
    p["loc"] = loc
    p["abroad"] = next((s["loc"]["abroad"] for s in sigs if s["loc"]["abroad"]), "")
    p["other_india"] = next((s["loc"]["other_india"] for s in sigs if s["loc"]["other_india"]), "")
    return p


def months_old(iso, today=None):
    """Whole months between a signal date and the as-of date (never negative)."""
    t = date.fromisoformat(today or config.TODAY)
    d = date.fromisoformat(iso)
    return max(0, (t.year - d.year) * 12 + (t.month - d.month))


def classify(p, today=None):
    """Returns (status, reason, unverified[]).  Order of checks = order of precedence."""
    mk, tier, loc, best = p["markers"], p["tier"], p["loc"], p["best"]
    buying = "purchase_intent" in mk
    nice = [m.replace("_", " ") for m in sorted(mk) if not m.startswith(("NEG_", "target_", "buy_in", "dubai_area", "regional_", "reply_")) and m not in ("advice_giver", "process_mention")]
    unv = ["identity behind the public handle", "financial capacity"]
    if "budget" in mk:
        unv.append("stated budget (self-reported)")
    if loc["tier"] == "explicit":
        unv.append("current residence (self-reported in the post)")
    elif loc["tier"] == "community":
        unv.append("residence (inferred from subreddit activity, not self-stated)")
    elif loc["tier"] == "mention":
        unv.append("residence (a South India place is named but the author does not say they live there)")
    elif "says_india" in mk:
        unv.append("residence (they say they are in India but not which state; the video's language is the only link to South India)")
    else:
        unv.append("residence (language / video audience is the only link to South India; could live anywhere, incl. the Gulf)")
    if "owner_investor" in mk:
        unv.append("the past purchase they describe (self-reported)")
    if "regional_language_text" in mk:
        unv.append("meaning of the regional-language comment (matched on keywords, not checked by a speaker)")
    if "found_on_review" in mk:
        unv.append("the reviewer's reading of the comment (one person, no second check)")
    if p.get("channel_country") == "IN":
        unv.append("state (their channel declares India, which does not say which state)")
    if p["had_contact"]:
        unv.append("author posted a phone/e-mail publicly - deliberately not collected")
    unv.append(f"whether still in the market (signal dated {best['date']})")

    # ---- rejections ---------------------------------------------------------
    if p["is_owner"]:
        return "reject", "Channel owner / video creator - promoter, not a buyer.", unv
    if p["any_agent"]:
        if p.get("agent_by_name"):
            return "reject", "The handle reads as a business name (property, realty, consultancy and the like), not a private person.", unv
        return "reject", "Agent/broker/seller language (offers services or solicits contact).", unv
    if not tier:
        return "reject", "Mentions Dubai property but asks nothing and shows no wish to buy.", unv
    if p.get("off_target") and not (mk & {"buy_in_dubai", "dubai_area"}):
        return "reject", f"Commented under a video that is not about Dubai property ({p['off_target']}); nothing in their own words points to Dubai.", unv
    # A renter or a seller is never a buyer, whatever else the comment contains, unless they also
    # say they want to buy. One incidental word ("salary", "avoid") does not outweigh a comment
    # that is otherwise specific about buying.
    specific = buying or (tier == "strong" and "advice_giver" not in mk)
    for neg, why in (("NEG_rent", "Looking to rent, not to buy."),
                     ("NEG_sell", "Wants to sell, not to buy."),
                     ("NEG_job", "Job-seeker context, not a property buyer."),
                     ("NEG_skeptic", "Critic/sceptic of Dubai property with no purchase intent."),
                     ("advice_giver", "Giving advice or opinion to others; no purchase intent of their own.")):
        excused = buying if neg in ("NEG_rent", "NEG_sell") else specific
        if neg in mk and not excused and not (neg == "advice_giver" and "buying_question" in mk):   # "what can you get..?" is a question, not advice
            return "reject", why, unv
    if "reply_to_other" in mk and tier != "strong":
        return "reject", "Reply in a discussion with another commenter; no clear purchase enquiry of their own.", unv
    if "target_india" in mk and not (mk & {"buy_in_dubai", "dubai_area", "comparison"}):
        return "reject", "Buying intent is for property in India, Dubai only mentioned in passing.", unv
    if p["other_india"] and LOC_RANK[loc["tier"]] < LOC_RANK["explicit"]:
        return "reject", f"States they are based in {p['other_india'].title()} - outside South India.", unv
    if p["abroad"] and LOC_RANK[loc["tier"]] < LOC_RANK["explicit"]:
        return "reject", f"States they live/work in {p['abroad'].title()} with no stated South India base.", unv
    cc = p.get("channel_country") or ""
    if cc and cc != "IN" and LOC_RANK[loc["tier"]] < LOC_RANK["explicit"]:
        return "reject", f"Their public channel country is {country_name(cc)}, outside India, and they state no South India base.", unv
    if p.get("activity_conflict") and LOC_RANK[loc["tier"]] < LOC_RANK["explicit"]:
        return "reject", f"Public activity points away from South India: {p['activity_conflict']}.", unv
    if not loc["tier"]:
        return "reject", "No evidence connecting the author to South India.", unv
    if "owner_investor" in mk and not (mk & {"purchase_intent", "buying_question", "budget"}) and LOC_RANK[loc["tier"]] < LOC_RANK["community"]:
        return "reject", "Says they already own property there; no sign of buying again and no stated South India base.", unv
    if tier == "weak" and "target_dubai" not in mk:
        return "reject", "Only a passing or general remark - no enquiry aimed at buying Dubai property.", unv
    if tier == "weak" and loc["tier"] != "context" and LOC_RANK[loc["tier"]] <= LOC_RANK["mention"]:
        return "reject", "Only asks for a price, details or a contact, and gives no location - nothing to qualify on.", unv

    # ---- needs validation / strong -----------------------------------------
    issues = []
    if tier != "strong":
        issues.append({"medium": "interest is in their own words but lacks specifics (no budget plus requirement, timeline or comparison)",
                       "weak": "only asks for a price, details or a contact; no stated wish to buy"}[tier])
    if "target_dubai" not in mk:
        issues.append("purchase target not explicitly Dubai in the quoted text")
    if LOC_RANK[loc["tier"]] < LOC_RANK["community"]:
        issues.append("South India link is weak (" + {"mention": "place named, not stated as residence", "language": "language only",
                                                  "context": "video audience only"}[loc["tier"]] + ")")
    if p["abroad"]:
        issues.append(f"says they currently live/work in {p['abroad'].title()} - South Indian origin but may not be based there")
    if cc and cc != "IN":
        issues.append(f"public channel country is {country_name(cc)} although they state a South India base")
    if p["other_india"]:
        issues.append(f"also references being based in {p['other_india'].title()}")
    if p.get("activity_other") and not p.get("activity_south") and loc["tier"] != "explicit":
        issues.append("more active in non-South-India city subreddits: " + ", ".join(p["activity_other"]))
    if "owner_investor" in mk and "purchase_intent" not in mk:
        issues.append("says they already bought; confirm whether they are buying again")
    if p.get("activity_dubai", 0) >= 20:
        issues.append(f"very active in Dubai communities ({p['activity_dubai']} items) - may be Dubai-based or in the trade")
    if "NEG_skeptic" in mk:
        issues.append("expresses doubts about the market")
    if p.get("read_home_elsewhere"):
        issues.append(f"the AI reader says they state a home outside South India ({p['read_home_elsewhere']}) - read the comment to confirm")
    if "found_on_review" in mk:
        issues.append("buying intent was read by the reviewer; no keyword rule matched it")
    if "read_by_ai" in mk:
        issues.append("buying intent was found by the AI reader, not by a keyword rule - read the comment to confirm")
    elif (p.get("read") or {}).get("intent") in ("none", "seller_or_agent"):
        issues.append("the AI reader saw no buying intent here (" + p["read"]["intent"].replace("_", " ") + ") - read the comment to confirm")
    if "regional_language_text" in mk:
        issues.append("comment is in a regional language - matched on keywords only, needs a human read")
    if "advice_giver" in mk and tier != "strong":
        issues.append("partly advising others")
    age = months_old(best["date"], today)
    if age > config.FRESH_MONTHS:
        issues.append(f"signal is {age} months old (older than {config.FRESH_MONTHS})")

    where = ", ".join(x for x in (loc["city"], loc["state"]) if x)
    if not issues:
        return ("strong_signal",
                f"Explicit Dubai buying intent with specifics ({', '.join(nice)}) and South India evidence ({loc['tier']}: {where}); signal {age} months old.",
                unv)
    return ("needs_validation",
            f"Signals: {', '.join(nice) or 'enquiry'}; location {loc['tier']} ({where}). To validate: " + "; ".join(issues) + ".",
            unv)


COUNTRY_NAMES = {"IN": "India", "AE": "UAE", "SA": "Saudi Arabia", "QA": "Qatar", "KW": "Kuwait", "OM": "Oman",
                 "BH": "Bahrain", "US": "USA", "GB": "UK", "CA": "Canada", "AU": "Australia", "SG": "Singapore",
                 "MY": "Malaysia", "DE": "Germany", "FR": "France", "LK": "Sri Lanka", "NZ": "New Zealand"}


def country_name(code):
    """Readable name for a two-letter country code ('' stays '')."""
    return COUNTRY_NAMES.get(code, code)


def prospect_id(p):
    return p["platform"][:2].upper() + "-" + hashlib.sha1(str(p["author_id"]).encode()).hexdigest()[:8]


FORWARD_INTENT = {"purchase_intent", "buying_question", "budget"}


def meets_both(p):
    """Not rejected, says in their own words they are looking to buy, and states a South India home.

    Someone who only says they already bought has shown no interest in buying now, so does not count."""
    return bool(p.get("status") != "reject" and p["markers"] & FORWARD_INTENT
                and p["loc"]["tier"] in ("explicit", "community"))


def rank_key(p, today=None):
    """Shortlist order: a stated wish to buy and specifics, plus location the person states themselves.

    Someone who meets both tests in their own words comes first. After that, forward intent with a
    specific (budget, timeline, comparison) outranks a bare question, an existing owner counts for
    less than someone who wants to buy now, and a signal older than the freshness limit is marked down."""
    mk = p["markers"]
    own_location = {"explicit": 5, "community": 4, "mention": 1}.get(p["loc"]["tier"], 0)
    intent = 3 if "purchase_intent" in mk else 1 if "buying_question" in mk else 0.5 if "owner_investor" in mk else 0
    specifics = min(3, len(mk & T.SPECIFICS))
    age = months_old(p["best"]["date"], today)
    stale = 3 if age > config.FRESH_MONTHS else 0
    return ((100 if meets_both(p) else 0)        # both tests in their own words always comes first
            + intent * 2 + specifics * 2 + own_location + (1 if "says_india" in mk else 0) - stale - age / 12.0)


COLUMNS = ["prospect_id", "public_name_or_handle", "platform", "city", "state", "location_confidence",
           "inferred_region", "channel_country", "location_evidence", "source_link", "signal_date", "signal_context", "evidence_of_interest",
           "intent_level", "intent_markers", "qualification_status", "meets_both_tests", "qualification_reason",
           "unverified_information", "review", "ai_reading", "signals_by_author", "other_source_links"]


def _evidence(p):
    """The person's own words: the best comment, anything else under the same video that adds to it,
    the comment that states their home if it is a different one, and the reviewer's quote if the
    shortened text does not already show it."""
    best = p["best"]
    parts = [_quote(best)] + [_quote(s, 160) for s in p.get("also", [])[:2]]
    home = next((s for s in p["signals"] if s is not best and s["loc"]["tier"] == "explicit" and s not in p.get("also", [])), None)
    if home is not None and p["loc"]["tier"] == "explicit":
        parts.append(_quote(home, 160))
    q = p.get("review_quote") or ""
    if q and not any(q in part for part in parts):
        parts.append("…" + q)
    return parts


def to_row(p):
    best, loc = p["best"], p["loc"]
    others = [s["url"] for s in p["signals"] if s is not best and s["in_scope"]][:4]
    # city/state are only filled when the author's own words or community activity support
    # them. A video's audience or a comment's language is an inference about a region, not
    # this person's city, so it goes in its own column.
    weak = loc["tier"] not in ("explicit", "community")
    region = ", ".join(x for x in (loc["city"], loc["state"]) if x)
    how = {"context": "video audience only", "language": "language only", "mention": "place mentioned, not stated as home"}.get(loc["tier"], "")
    both = meets_both(p)
    return {
        "prospect_id": p.get("id") or prospect_id(p),
        "public_name_or_handle": p["name"],
        "platform": p["platform"],
        "city": "unknown" if weak else (loc["city"] or "unknown"),
        "state": "unknown" if weak else (loc["state"] or "unknown"),
        "location_confidence": loc["tier"] or "none",
        "inferred_region": f"{region} ({how})" if weak and region and how else "",
        "channel_country": country_name(p.get("channel_country") or ""),
        "location_evidence": loc["evidence"],
        "source_link": best["url"],
        "signal_date": best["date"],
        "signal_context": (best["context"] + (" - " + best["context_title"][:90] if best.get("context_title") else "")),
        "evidence_of_interest": " / ".join(_evidence(p)),
        "intent_level": p["tier"] or "none",
        "intent_markers": ", ".join(sorted(m for m in p["markers"] if not m.startswith("NEG_"))),
        "qualification_status": p["status"],
        "meets_both_tests": "yes" if both else "no",
        "qualification_reason": p["reason"],
        "unverified_information": "; ".join(p["unverified"]),
        "review": p.get("review", "automatic"),
        "ai_reading": read_summary(p),
        "signals_by_author": p["n_signals"],
        "other_source_links": " ".join(others),
    }

"""Text signals: redaction, location evidence, buying-intent markers, disqualifiers.

Everything here is a transparent rule so each classification can be explained.
"""
import re
import unicodedata

from prospector import lexicon as L

# ---------------------------------------------------------------- redaction --
_PHONE = re.compile(r"(?<!\d)(?:\+|00)?\d(?:[\s\-()./]{0,5}\d){8,13}(?!\d)")       # 9 to 14 digits
_MONEY_BEFORE = re.compile(r"(?:budget|aed|dhs?|dirhams?|rs\.?|inr|₹|usd|\$|price|cost|worth|around|approx\w*|upto|up\s+to|under|below|within)\W{0,3}$", re.I)
_MONEY_AFTER = re.compile(r"^\W{0,2}(?:aed|dhs?|dirhams?|lakhs?|lacs?|crores?|cr|inr|rs|rupees|usd|million|mn|k\b|sq\.?\s?ft|sqft)", re.I)
# an Indian or UAE mobile number, with or without the country code: redacted whatever surrounds it
_MOBILE = re.compile(r"^(?:(?:00)?91|0)?[6-9]\d{9}$|^(?:(?:00)?971|0)?5\d{8}$")
_DATE_YMD = re.compile(r"(?:19|20)\d\d[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)")
_DATE_DMY = re.compile(r"(\d{1,2})[-/.](\d{1,2})[-/.](?:19|20)\d\d(?!\d)")


def _redact_phone(m):
    """Replace a phone-like digit run, but leave dates and numeric ranges alone."""
    s = m.group(0)
    d = _DATE_YMD.match(s)
    if d and 1 <= int(d.group(1)) <= 12 and 1 <= int(d.group(2)) <= 31:
        return s                                   # 2026-11-11 10:30
    d = _DATE_DMY.match(s)
    if d and 1 <= int(d.group(1)) <= 31 and 1 <= int(d.group(2)) <= 12:
        return s                                   # 11/11/2026 10:30
    digits = re.sub(r"\D", "", s)
    if _MOBILE.match(digits):
        return PHONE_TOKEN                         # shaped like a mobile number: never an amount
    groups = re.findall(r"\d+", s)
    if len(groups) == 2 and min(map(len, groups)) >= 6:
        return s                                   # 850000 - 1200000 is a price range
    text = m.string
    if _MONEY_BEFORE.search(text[max(0, m.start() - 16):m.start()]) or _MONEY_AFTER.match(text[m.end():m.end() + 12]):
        return s                                   # "Budget 1 000 000 - 1 500 000 AED" is an amount
    return PHONE_TOKEN
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_LINK = re.compile(r"https?://\S+|www\.\S+|\b(?:wa\.me|t\.me|bit\.ly|linktr\.ee)/\S+", re.I)
# "insta: @name", "telegram - name", "whatsapp @name" ... a handle on another platform is a contact detail
_SOCIAL = re.compile(r"\b(insta(?:gram)?|ig|telegram|tg|snap(?:chat)?|fb|facebook|skype|linkedin|whats\s?app)"
                     r"(\s*(?:id|handle|username|user)?(?:\s*[:=]\s*@?|\s*@|\s+-\s+@?)|\s+(?:id\s+|handle\s+|is\s+)?(?!\d\s*(?:bhk|br|bed|cr|lakh|lac|k\b|m\b))(?=[\w.]*[\d._]))([\w.]{3,})", re.I)
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)
LINK_TOKEN, PHONE_TOKEN, EMAIL_TOKEN, HANDLE_TOKEN = "[link removed]", "[phone removed]", "[email removed]", "[handle removed]"


def clean_text(text):
    """Normalise and redact a public post/comment before it is cached, classified or exported.

    - NFKC folds "fancy" Unicode letters (𝘿𝙧𝙚𝙖𝙢 -> Dream) that adverts use to dodge filters
    - e-mail addresses, phone numbers, links and off-platform handles are replaced by tokens
    Idempotent. Returns (clean_text, had_contact_detail).
    """
    text = unicodedata.normalize("NFKC", text or "")
    # zero-width joiners are meaningful inside Indic scripts, so only strip them at the edges
    text = text.strip().strip("\u200b\u200c\u200d\u2060\ufeff").strip()
    out = _EMAIL.sub(EMAIL_TOKEN, text)
    out = _LINK.sub(LINK_TOKEN, out)
    out = _PHONE.sub(_redact_phone, out)
    out = _SOCIAL.sub(lambda m: m.group(1) + m.group(2) + HANDLE_TOKEN, out)
    had_contact = any(t in out for t in (PHONE_TOKEN, EMAIL_TOKEN, HANDLE_TOKEN))
    return out, had_contact


# ----------------------------------------------------------------- location --
_VIRAMA = "்్್്"       # Tamil, Telugu, Kannada, Malayalam


def _stem(word):
    """Native place names inflect ("சென்னையில்", "కొచ్చిలో"): match on the stem without a final virama."""
    return word[:-1] if word and word[-1] in _VIRAMA else word


def _alt(words):
    latin = sorted((w for w in words if w.isascii()), key=len, reverse=True)
    native = sorted({_stem(w) for w in words if not w.isascii()}, key=len, reverse=True)
    parts = []
    if latin:
        parts.append(r"\b(?:" + "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in latin) + r")\b")
    if native:
        parts.append("(?:" + "|".join(map(re.escape, native)) + ")")
    return "|".join(parts)


_SOUTH_LOOKUP = {}
for _state, _cities in L.SOUTH_PLACES.items():
    for _city, _aliases in _cities.items():
        for _a in _aliases:
            _SOUTH_LOOKUP[_a] = (_city, _state)
            _SOUTH_LOOKUP[_stem(_a)] = (_city, _state)
_SOUTH_RE = re.compile(_alt(_SOUTH_LOOKUP), re.I)
_ABROAD_RE = re.compile(_alt(L.ABROAD_PLACES), re.I)
_OTHER_IN_RE = re.compile(_alt(L.OTHER_INDIA_PLACES), re.I)

# A residence statement must be about the speaker: a first-person subject shortly before
# the verb, or the verb opening a sentence ("Living in Kochi."), and must not be negated.
_SUBJ = (r"(?:\b(?:i|we|i'm|im|iam|i\s+am|am|we\s+are|we're|myself|me|currently|presently)\b[^.!?\n]{0,40}?"
         r"|(?:^|[.!?\n,;:(\-])\s*)")
_RESIDE = (_SUBJ + r"\b(?:live|lives|living|stay|stays|staying|reside|residing|settled|based|located|work|works|working|"
           r"born|brought\s+up|moved|relocated|shifted)\s+(?:\w+\s+){0,2}?(?:in|at|out\s+of|near|to)\s+(?:the\s+)?$")
_IAM = (r"\b(?:i\s*am|i'm|im|iam|i\s+m|we\s*are|we're|am|me|watching)\s+(?:currently\s+|now\s+|also\s+|an?\s+\w+\s+)?"
        r"(?:in|at|from)\s+(?:the\s+)?$")
_HERE = r"\bhere\s+(?:in|at)\s+$|\bnative\s+(?:is\s+|place\s+(?:is\s+)?|of\s+)?$|\bhail(?:ing)?\s+from\s+$"
# "I am living chennai" - the preposition is often dropped
_IAM_VERB = (r"\b(?:i\s*am|i'm|im|iam|i\s+m|we\s*are|we're|am)\s+(?:currently\s+|now\s+)?"
             r"(?:living|staying|residing|working|settled|based)\s+(?:in\s+|at\s+)?$")
# romanised and native first-person pronouns: "naan Madurai la irukken", "njan Kochi il aanu",
# "nenu Hyderabad nundi", "naanu Bangalore alli", "நான் மதுரையில் இருக்கிறேன்"
_REGIONAL_I = (r"(?:\b(?:naan|nan|naa|naanga|njan|nyan|njangal|nenu|nen|memu|naanu|nanu|naavu)\b|நான்|நாங்கள்|ഞാൻ|ഞങ്ങൾ|నేను|మేము|ನಾನು|ನಾವು)"
               r"\s+(?:\S+\s+){0,2}$")
_FROM = r"(?:^|[.!?\n,;:(\-])\s*from\s+(?:the\s+)?$"      # "Interested, from Kochi" - not "investors from Kochi"
_PRE_SELF = re.compile(f"(?:{_RESIDE}|{_IAM}|{_HERE}|{_IAM_VERB}|{_REGIONAL_I})", re.I)
_PRE_FROM = re.compile(_FROM, re.I)
_NEGATED = re.compile(r"\b(?:not|never|no\s+longer|don'?t|do\s+not|isn'?t|aren'?t|wasn'?t)\b[^.!?\n]{0,25}$", re.I)
# "Chennai based" only describes the author when the author is the subject ("I am a Chennai-based investor")
_POST_SELF = re.compile(r"^\s*(?:-\s*)?(?:based|resident|native|here\b|guy|person|folk|ite\b)", re.I)
# romanised "am in X": "Abudhabi anu" (Malayalam), "Chennai la irukken" (Tamil), "Hyderabad lo unnanu" (Telugu)
_POST_REGIONAL = re.compile(r"^\s*(?:il|yil|la|le|lo|alli)?\s*(?:anu|aanu|aan|irukken|irukkiren|irukkom|unnanu|unnam|iddini|iddivi)\b", re.I)
_FIRST_PERSON = re.compile(r"\b(?:i|we|i'm|im|iam|am|me|myself|my)\b", re.I)
# stricter forms, used for places outside South India
_IAM_STRICT = (r"\b(?:i\s*am|i'm|im|iam|i\s+m|we\s*are|we're)\s+(?:currently\s+|now\s+|also\s+|an?\s+\w+\s+)?"
               r"(?:in|at|from)\s+(?:the\s+)?$")
_PRE_STRICT = re.compile(f"(?:{_RESIDE}|{_IAM_STRICT}|{_HERE}|{_IAM_VERB})", re.I)
_REGIONAL_I_RE = re.compile(_REGIONAL_I, re.I)
_POST_RESIDES = re.compile(r"^\s*(?:il|yil|la|le|lo|alli)?\s*(?:irukken|irukkiren|irukkom|unnanu|unnam|iddini|iddivi|thamasam|thamasikkunnu)\b", re.I)
# "Ipo Abudhabi anu, ..." ends the clause: a statement of where they are. "Dubai il aanu nalla
# investment" goes on to say something about Dubai.
_POST_COPULA_END = re.compile(r"^\s*(?:il|yil|la|le|lo|alli)?\s*(?:anu|aanu|aan)\s*(?:[,.!?\n]|$)", re.I)
# "want to get settled in Dubai", "planning to move to Kochi" is a plan, not where they are now
_FUTURE = re.compile(r"\b(?:get|to|will|would|wanna|gonna)\s+(?:be\s+)?(?:settled?|live|stay|move|shift|relocate)\s+(?:\w+\s+){0,2}?(?:in|at|to)\s+(?:the\s+)?$", re.I)
_ROUTE = re.compile(r"^\s*(?:to|-|–|→|->)\s", re.I)        # "from Chennai to Dubai" is a route, not a home


def _self_stated(text, m, allow_bare_from, strict=False):
    """Does the author say this place is where they are?

    strict is used for places outside South India, where a wrong "yes" throws a buyer away:
    "naan Dubai la oru 2BHK vaanganum" names Dubai as where the flat is, not where the author is.
    There a regional pronoun must be closed by a verb ("naan Dubai la irukken"), and "guide me in
    Dubai" does not count."""
    pre = text[max(0, m.start() - 70):m.start()]
    post = text[m.end():m.end() + 22]
    if _NEGATED.search(pre) or _FUTURE.search(pre):
        return False
    if strict:
        if _PRE_STRICT.search(pre) or _POST_RESIDES.match(post) or _POST_COPULA_END.match(post):
            return True
        if _REGIONAL_I_RE.search(pre) and _POST_REGIONAL.match(post):
            return True
        return bool(_POST_SELF.search(post) and _FIRST_PERSON.search(pre))
    if _PRE_SELF.search(pre) or _POST_REGIONAL.match(post):
        return True
    if _POST_SELF.search(post) and _FIRST_PERSON.search(pre):
        return True
    return bool(allow_bare_from and _PRE_FROM.search(pre) and not _ROUTE.match(post))


def find_location(text):
    """Location evidence found in the text itself.

    Returns dict(tier, city, state, quote, abroad, other_india) where tier is
    'explicit' (the author says they live in / are from a South India place),
    'mention' (a South India place is named without a residence statement) or ''.
    """
    text = text or ""
    best = {"tier": "", "city": "", "state": "", "quote": "", "abroad": "", "other_india": ""}
    for m in _SOUTH_RE.finditer(text):
        hit = re.sub(r"\s+", " ", m.group(0).lower())
        city, state = _SOUTH_LOOKUP.get(hit, ("", ""))
        if not state:
            continue
        tier = "explicit" if _self_stated(text, m, allow_bare_from=True) else "mention"
        better = (tier == "explicit" and best["tier"] != "explicit") or not best["tier"] \
            or (tier == best["tier"] and city and not best["city"])
        if better:
            q = text[max(0, m.start() - 60):m.end() + 40].replace("\n", " ").strip()
            best.update(tier=tier, city=city, state=state, quote=q)
    for rx, key in ((_ABROAD_RE, "abroad"), (_OTHER_IN_RE, "other_india")):
        for m in rx.finditer(text):
            if _self_stated(text, m, allow_bare_from=False, strict=True):
                best[key] = m.group(0)
                break
    return best


def detect_script(text):
    """Returns 'ta' / 'ml' / 'te' / 'kn' if the text contains that script, else ''."""
    counts = {}
    for ch in text or "":
        o = ord(ch)
        for lang, (lo, hi) in L.SCRIPT_RANGES.items():
            if lo <= o <= hi:
                counts[lang] = counts.get(lang, 0) + 1
    return max(counts, key=counts.get) if counts else ""


# ------------------------------------------------------------------- intent --
def _any(patterns, t):
    return any(re.search(p, t, re.I) for p in patterns)


_DUBAI = re.compile(L.DUBAI, re.I)
_PROP = re.compile(L.PROPERTY, re.I)
_INVEST = re.compile(L.INVEST, re.I)
_AMOUNT = re.compile(L.AMOUNT, re.I)
_BUDGET_WORD = re.compile(L.BUDGET_WORD, re.I)
_BUDGET_HAVE = re.compile(L.BUDGET_HAVE + L.AMOUNT, re.I)
_BUDGET_ASK = re.compile(L.BUDGET_ASK_PRE + L.AMOUNT + L.BUDGET_ASK_POST, re.I)
_NOT_ME = re.compile(L.NOT_FIRST_PERSON, re.I)
_PURCHASE = [re.compile(p, re.I) for p in L.PURCHASE]
_NATIVE_NEG = re.compile(L.NATIVE_NEGATION)
_NOT_PROPERTY = re.compile(L.NOT_PROPERTY, re.I)
_BOOK_ONLY = re.compile(r"\bbook(?:ing)?\b(?!.*\b(?:buy|buying|invest|investing|purchase|purchasing|own|owning)\b)", re.I)
_I_BEFORE = re.compile(r"\b(?:i|we|i'm|im|iam|am)\s+(?:\w+\s+){0,2}$", re.I)
_NEG_BEFORE = re.compile(r"\b(?:no|not|don'?t|never|cannot|can'?t|won'?t|didn'?t)\s+(?:\w+\s+){0,2}$", re.I)
_QUESTION = re.compile(L.QUESTION, re.I)
_ENQUIRY_TOPIC = re.compile(L.ENQUIRY_TOPIC, re.I)
_REQUEST_CUE = re.compile(L.REQUEST_CUE, re.I)
# the topic word is a whole sentence: "price", "Details pls", "price?" - but not "nice price"
_BARE_TOPIC = re.compile(r"(?:^|[.!?\n])[^\w.!?\n]*(?:" + L.ENQUIRY_TOPIC + r")(?:\s+(?:pls|plz|please|bro|sir|madam|mam|ji|anna|chetta|chechi))?"
                         r"[^\w.!?\n]*(?:$|[.!?\n])", re.I)
_DETAILS = re.compile(r"\bdetails?\b", re.I)
_SAYS_INDIA = re.compile(r"\b(?:from|frm|in)\s+india\b", re.I)
_AGENT_NAME = re.compile(L.AGENT_NAME, re.I)


def is_dubai_property(text):
    """True when the text is about Dubai/UAE AND property (or investing in it)."""
    t = text or ""
    return bool(_DUBAI.search(t) and (_PROP.search(t) or _INVEST.search(t)))


def _first_person_purchase(t):
    """A buying phrase whose subject is the author - not 'you', 'my brother', 'investors', and not denied."""
    for rx in _PURCHASE:
        for m in rx.finditer(t):
            before = t[max(0, m.start() - 40):m.start()]
            if _NEG_BEFORE.search(before):
                continue                                   # "I don't want to buy"
            if not m.group(0).isascii() and _NATIVE_NEG.search(t[m.end():m.end() + 14]):
                continue                                   # native script "... cannot buy"
            around = t[max(0, m.start() - 28):m.end() + 28]
            if _NOT_PROPERTY.search(around) and not _PROP.search(t):
                continue                                   # gold, a car, tickets, "Burj Khalifa 😂"
            if _BOOK_ONLY.search(m.group(0)) and not _PROP.search(t):
                continue                                   # "planning to book tickets"
            if _I_BEFORE.search(before) or not _NOT_ME.search(before):
                return True                                # "bro I want to buy" is still the author
    return False


def markers(text):
    """Set of marker names found in one piece of text."""
    t = unicodedata.normalize("NFKC", text or "").lower()
    out = set()
    if _first_person_purchase(t):
        out.add("purchase_intent")
    if _AMOUNT.search(t) and (_BUDGET_WORD.search(t) or _BUDGET_HAVE.search(t) or _BUDGET_ASK.search(t)):
        out.add("budget")
    if detect_script(t):
        out.add("regional_language_text")
    if _any(L.TIMELINE, t):
        out.add("timeline")
    if _any(L.REQUIREMENT, t):
        out.add("requirement")
    asking = bool(_QUESTION.search(t))
    if _any(L.PROCESS, t):
        out.add("process_question" if asking else "process_mention")
    # a short question about the process or about a specific unit, area or payment term
    # ... but "golden visa related details???" only asks for details, like "details please"
    only_details = bool(_DETAILS.search(t)) and len(t.split()) <= 6
    renting = bool(re.search(L.RENT, t)) and "purchase_intent" not in out
    if (asking and len(t) <= L.BUYING_QUESTION_MAX_CHARS and out & {"process_question", "requirement"}
            and not only_details and not renting):
        out.add("buying_question")
    if _any(L.COMPARISON, t):
        out.add("comparison")
    words = len(t.split())
    if _any(L.ENQUIRY, t) or _BARE_TOPIC.search(t) or (
            _ENQUIRY_TOPIC.search(t) and words <= L.ENQUIRY_MAX_WORDS and (asking or _REQUEST_CUE.search(t))):
        out.add("enquiry")
    if re.search(L.OWNER_INVESTOR, t):
        out.add("owner_investor")
    if _any(L.AGENT, t) or (LINK_TOKEN in t and re.search(L.PROMO_WITH_LINK, t)):
        out.add("NEG_agent")
    if re.search(L.JOB, t):
        out.add("NEG_job")
    if re.search(L.RENT, t):
        out.add("NEG_rent")
    if re.search(L.SELL, t):
        out.add("NEG_sell")
    if re.search(L.SKEPTIC, t):
        out.add("NEG_skeptic")
    if re.search(L.ADVICE_GIVER, t):
        out.add("advice_giver")
    if _SAYS_INDIA.search(t):
        out.add("says_india")           # "how to invest from India": in India, state unknown
    return out


WEIGHTS = {"purchase_intent": 3, "budget": 3, "requirement": 2, "buying_question": 2, "owner_investor": 2, "timeline": 1,
           "comparison": 1, "process_question": 1.5, "process_mention": 0.5, "enquiry": 1}
SPECIFICS = {"budget", "timeline", "requirement", "comparison", "process_question"}
OWN_WORDS = {"purchase_intent", "budget", "buying_question", "owner_investor"}     # medium intent or better


def intent_tier(mk):
    """strong / medium / weak / '' from a set of markers.

    strong = a first-person wish to buy or invest PLUS a concrete specific (budget, timeline,
             requirement, comparison, process question) - or a stated budget plus a
             requirement or timeline.
    medium = intent in the author's own words without specifics: a wish to buy, a budget,
             a buying question ("how much down payment?"), or an existing purchase.
    weak   = only a request for price, details or a contact, or "interested".
    """
    score = sum(WEIGHTS.get(m, 0) for m in mk)
    spec = mk & SPECIFICS
    if ("purchase_intent" in mk and spec) or ("budget" in mk and (mk & {"requirement", "timeline"})):
        return "strong", score
    if mk & OWN_WORDS:
        return "medium", score
    if "enquiry" in mk:
        return "weak", score
    return "", score


def is_business_name(name):
    return bool(_AGENT_NAME.search(name or ""))

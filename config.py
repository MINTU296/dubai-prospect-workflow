"""All tunables for the workflow live here: sources, queries, thresholds.

Change this file (not the code) to re-target the workflow.
"""
from datetime import date

# ----------------------------------------------------------------------------
# Run window and volume
# ----------------------------------------------------------------------------
SIGNAL_AFTER = "2025-01-01"      # ignore buying signals older than this at collection time
FRESH_MONTHS = 18                # a signal older than this cannot be "strong" (people buy or move on)
CANDIDATE_CAP = None             # optional maximum rows in the sheet; None lists every candidate
TODAY = date.today().isoformat()   # "as of" date for freshness; override per run with --as-of

# ----------------------------------------------------------------------------
# Reliability and data retention
# ----------------------------------------------------------------------------
HTTP_TIMEOUT_SEC = 60            # per request
CACHE_TTL_HOURS = 24             # cached API answers older than this are refetched (stale copy kept as fallback)
CACHE_RETENTION_DAYS = 30        # cached public text is deleted after this many days

# ----------------------------------------------------------------------------
# Hooks for a forum-type source. None is used: the workflow reads YouTube only.
# qualify.py can treat activity in a location-specific community as location evidence
# (the "community" tier); these tables say which community names mean what.
# ----------------------------------------------------------------------------
SOUTH_SUBREDDITS = {
    "bangalore": ("Bengaluru", "Karnataka"),
    "bengaluru": ("Bengaluru", "Karnataka"),
    "Bengaluru": ("Bengaluru", "Karnataka"),
    "karnataka": ("", "Karnataka"),
    "mangalore": ("Mangaluru", "Karnataka"),
    "mysore": ("Mysuru", "Karnataka"),
    "hyderabad": ("Hyderabad", "Telangana"),
    "telangana": ("", "Telangana"),
    "Chennai": ("Chennai", "Tamil Nadu"),
    "TamilNadu": ("", "Tamil Nadu"),
    "Coimbatore": ("Coimbatore", "Tamil Nadu"),
    "Kerala": ("", "Kerala"),
    "Kochi": ("Kochi", "Kerala"),
    "Trivandrum": ("Thiruvananthapuram", "Kerala"),
    "Kozhikode": ("Kozhikode", "Kerala"),
    "andhra_pradesh": ("", "Andhra Pradesh"),
    "Visakhapatnam": ("Visakhapatnam", "Andhra Pradesh"),
    "Vijayawada": ("Vijayawada", "Andhra Pradesh"),
}
DUBAI_SUBS = {"dubairealestate", "DubaiRealEstate", "dubai", "DubaiCentral", "UAE"}
ENRICH_MAX_AUTHORS = 80          # at most this many authors are passed to an activity lookup, if one is supplied

# ----------------------------------------------------------------------------
# Source: YouTube comments (official YouTube Data API v3, free key)
# ----------------------------------------------------------------------------
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
YOUTUBE_QUOTA_BUDGET = 8000      # daily free quota is 10,000 units; search costs 100, the rest 1
YOUTUBE_RETRIES = 3              # attempts per request on network errors, 429 and 5xx
YOUTUBE_BACKOFF_SEC = 2.0        # first backoff; doubles each attempt
YOUTUBE_MAX_CONSECUTIVE_FAILURES = 5   # circuit breaker: after this many failed requests in a row, use cache only
YOUTUBE_RESULTS_PER_QUERY = 25
YOUTUBE_MAX_VIDEOS = 160
YOUTUBE_MIN_COMMENTS = 1
YOUTUBE_COMMENT_PAGES = 20       # x100 comment threads per video; each thread carries at most 5 of its replies
# Anchor search: on Dubai-property videos by Indian creators in ANY language, ask the API
# only for comments that name a South India place (commentThreads.searchTerms, 1 unit each).
YOUTUBE_ANCHOR_TERMS = ["Bangalore", "Bengaluru", "Hyderabad", "Chennai", "Kerala", "Kochi", "Coimbatore",
                        "Tamil Nadu", "Telangana", "Andhra", "Karnataka", "Vizag", "Mysore", "Trivandrum"]
YOUTUBE_ANCHOR_VIDEOS = 70       # most-commented relevant videos to anchor-search
YOUTUBE_ANCHOR_MIN_COMMENTS = 30
# Look up the country a candidate's channel publicly declares (channels.list, 1 unit per 50
# channels). Most channels leave it blank; one set to a country other than India is treated
# like a commenter saying they live abroad. Only the country code is requested and cached.
YOUTUBE_CHANNEL_COUNTRY = True
# Search queries. Regional-language videos about buying Dubai property attract viewers from
# that language region; a video's language is read from the video itself, never from the query.
YOUTUBE_QUERIES = [
    "Dubai property investment Tamil",
    "Dubai apartment buy from India Tamil",
    "துபாய் வீடு வாங்க",
    "துபாய் ரியல் எஸ்டேட் முதலீடு",
    "Dubai property investment Malayalam",
    "Dubai flat buy Malayalam",
    "ദുബായ് പ്രോപ്പർട്ടി നിക്ഷേപം",
    "ദുബായ് ഫ്ലാറ്റ് വാങ്ങാൻ",
    "Dubai property investment Telugu",
    "Dubai real estate buy from India Telugu",
    "దుబాయ్ ప్రాపర్టీ పెట్టుబడి",
    "Dubai property investment Kannada",
    "ದುಬೈ ಪ್ರಾಪರ್ಟಿ ಹೂಡಿಕೆ",
    "Dubai property expo Bangalore",
    "Dubai property show Hyderabad",
    "Dubai real estate expo Chennai",
    "Dubai property show Kochi Kerala",
    "Dubai vs Bangalore real estate investment",
    "Dubai vs Hyderabad real estate investment",
    "buy Dubai property from India LRS",
    "Dubai real estate Tamil",
    "துபாய் சொத்து முதலீடு",
    "Dubai la veedu vangalama",
    "Dubai apartment price Tamil",
    "Dubai property investment Chennai Coimbatore",
    "Dubai real estate Malayalam",
    "ദുബായ് റിയൽ എസ്റ്റേറ്റ്",
    "ദുബായിൽ വീട് വാങ്ങാൻ",
    "Dubai villa apartment price Malayalam",
    "Dubai property Kerala investors",
    "Dubai real estate Telugu",
    "దుబాయ్ రియల్ ఎస్టేట్",
    "దుబాయ్ లో ఇల్లు కొనడం",
    "Dubai flats price Telugu",
    "Dubai property Hyderabad investors",
    "Dubai real estate Kannada",
    "ದುಬೈ ರಿಯಲ್ ಎಸ್ಟೇಟ್",
    "Dubai property Bangalore investors",
    "Dubai property Vizag Vijayawada investors",
    "Dubai property roadshow Kochi Bangalore Chennai",
    "Dubai real estate for Indians should you buy",
    "Indians buying property in Dubai explained",
    "Dubai property investment from India",
    "Dubai property Tamil price lakhs",
    "Dubai apartment for sale Malayalam",
    "Dubai villa flat price Telugu lakhs",
    "Dubai property expo Chennai",
    "Dubai property show Coimbatore Madurai",
    "Dubai property exhibition Kochi Calicut",
    "Dubai property expo Hyderabad",
    "Danube Sobha Emaar Dubai Tamil",
    "Danube Sobha Emaar Dubai Malayalam",
    "Danube Sobha Emaar Dubai Telugu",
    "Dubai real estate investment Kerala NRI Malayalam",
]


# ---- optional AI reading (run.py --ai-read; needs ANTHROPIC_API_KEY) --------------------
AI_MODEL = "claude-opus-5-5"
AI_EFFORT = "low"              # a labelling task: low effort is enough and keeps it quick
AI_BATCH_SIZE = 20             # people per request
AI_WORKERS = 4                 # requests in flight at once


def validate():
    """Fail fast on a mis-edited config. Returns a list of problems (empty = fine)."""
    problems = []
    for name in ("SIGNAL_AFTER", "TODAY"):
        try:
            date.fromisoformat(globals()[name])
        except (TypeError, ValueError):
            problems.append(f"{name} must be an ISO date (YYYY-MM-DD), got {globals()[name]!r}")
    if CANDIDATE_CAP is not None and (not isinstance(CANDIDATE_CAP, int) or CANDIDATE_CAP <= 0):
        problems.append(f"CANDIDATE_CAP must be None or a positive whole number, got {CANDIDATE_CAP!r}")
    if AI_EFFORT not in ("low", "medium", "high", "xhigh", "max"):
        problems.append(f"AI_EFFORT must be low, medium, high, xhigh or max, got {AI_EFFORT!r}")
    if not (isinstance(AI_MODEL, str) and AI_MODEL.strip()):
        problems.append(f"AI_MODEL must be a model id, got {AI_MODEL!r}")
    for name in ("FRESH_MONTHS", "HTTP_TIMEOUT_SEC", "AI_BATCH_SIZE", "AI_WORKERS",
                 "YOUTUBE_QUOTA_BUDGET", "YOUTUBE_RETRIES", "YOUTUBE_RESULTS_PER_QUERY", "YOUTUBE_COMMENT_PAGES"):
        v = globals()[name]
        if not isinstance(v, (int, float)) or v <= 0:
            problems.append(f"{name} must be a positive number, got {v!r}")
    for i, row in enumerate(YOUTUBE_QUERIES):
        if not (isinstance(row, str) and row.strip()):
            problems.append(f"YOUTUBE_QUERIES[{i}] must be a non-empty search string, got {row!r}")
    for name in ("YOUTUBE_MAX_VIDEOS", "YOUTUBE_ANCHOR_VIDEOS", "YOUTUBE_MIN_COMMENTS", "YOUTUBE_ANCHOR_MIN_COMMENTS",
                 "YOUTUBE_MAX_CONSECUTIVE_FAILURES", "CACHE_RETENTION_DAYS"):
        v = globals()[name]
        if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
            problems.append(f"{name} must be a positive whole number, got {v!r}")
    if CACHE_TTL_HOURS is not None and (isinstance(CACHE_TTL_HOURS, bool) or not isinstance(CACHE_TTL_HOURS, (int, float)) or CACHE_TTL_HOURS < 0):
        problems.append(f"CACHE_TTL_HOURS must be None or a number of hours, got {CACHE_TTL_HOURS!r}")
    if not (0 < YOUTUBE_RESULTS_PER_QUERY <= 50):
        problems.append("YOUTUBE_RESULTS_PER_QUERY must be between 1 and 50 (API limit)")
    return problems

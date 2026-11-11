"""Gazetteers and keyword patterns. Pure data, no logic."""

# state -> canonical city -> aliases (lower-case Latin, or native script)
SOUTH_PLACES = {
    "Karnataka": {
        "": ["karnataka", "ಕರ್ನಾಟಕ"],
        "Bengaluru": ["bangalore", "bengaluru", "banglore", "bangaluru", "blr", "whitefield",
                      "koramangala", "indiranagar", "electronic city", "hsr layout", "sarjapur",
                      "ಬೆಂಗಳೂರು"],
        "Mysuru": ["mysore", "mysuru", "ಮೈಸೂರು"],
        "Mangaluru": ["mangalore", "mangaluru", "ಮಂಗಳೂರು"],
        "Hubballi-Dharwad": ["hubli", "hubballi", "dharwad", "ಹುಬ್ಬಳ್ಳಿ"],
        "Belagavi": ["belgaum", "belagavi", "ಬೆಳಗಾವಿ"],
        "Udupi": ["udupi", "manipal", "ಉಡುಪಿ"],
        "Shivamogga": ["shimoga", "shivamogga"],
        "Davanagere": ["davangere", "davanagere"],
        "Kalaburagi": ["gulbarga", "kalaburagi"],
        "Tumakuru": ["tumkur", "tumakuru"],
    },
    "Kerala": {
        "": ["kerala", "കേരള"],
        "Kochi": ["kochi", "cochin", "ernakulam", "kakkanad", "കൊച്ചി", "എറണാകുളം"],
        "Thiruvananthapuram": ["trivandrum", "thiruvananthapuram", "tvm", "തിരുവനന്തപുരം"],
        "Kozhikode": ["calicut", "kozhikode", "കോഴിക്കോട്"],
        "Thrissur": ["thrissur", "trichur", "തൃശൂർ"],
        "Kannur": ["kannur", "കണ്ണൂർ"],
        "Kollam": ["kollam", "കൊല്ലം"],
        "Malappuram": ["malappuram", "മലപ്പുറം"],
        "Kottayam": ["kottayam", "കോട്ടയം"],
        "Palakkad": ["palakkad", "palghat", "പാലക്കാട്"],
        "Alappuzha": ["alappuzha", "alleppey", "ആലപ്പുഴ"],
        "Kasaragod": ["kasaragod", "kasargod"],
        "Pathanamthitta": ["pathanamthitta"],
        "Wayanad": ["wayanad", "വയനാട്"],
    },
    "Tamil Nadu": {
        "": ["tamil nadu", "tamilnadu", "தமிழ்நாடு"],
        "Chennai": ["chennai", "madras", "சென்னை"],
        "Coimbatore": ["coimbatore", "kovai", "கோயம்புத்தூர்", "கோவை"],
        "Madurai": ["madurai", "மதுரை"],
        "Tiruchirappalli": ["trichy", "tiruchirappalli", "tiruchi", "திருச்சி"],
        "Salem": ["salem", "சேலம்"],
        "Tiruppur": ["tirupur", "tiruppur", "திருப்பூர்"],
        "Erode": ["erode", "ஈரோடு"],
        "Tirunelveli": ["tirunelveli", "nellai", "திருநெல்வேலி"],
        "Vellore": ["vellore", "வேலூர்"],
        "Thoothukudi": ["tuticorin", "thoothukudi", "தூத்துக்குடி"],
        "Thanjavur": ["thanjavur", "tanjore", "தஞ்சாவூர்"],
        "Hosur": ["hosur", "ஓசூர்"],
        "Nagercoil": ["nagercoil", "kanyakumari", "நாகர்கோவில்", "கன்னியாகுமரி"],
    },
    "Telangana": {
        "": ["telangana", "తెలంగాణ"],
        "Hyderabad": ["hyderabad", "hyd", "kokapet", "కోకాపేట", "secunderabad", "gachibowli", "hitech city", "hi-tech city",
                      "kondapur", "kokapet", "హైదరాబాద్"],
        "Warangal": ["warangal", "వరంగల్"],
        "Karimnagar": ["karimnagar", "కరీంనగర్"],
        "Nizamabad": ["nizamabad"],
        "Khammam": ["khammam", "ఖమ్మం"],
    },
    "Andhra Pradesh": {
        "": ["andhra pradesh", "andhra", "ఆంధ్ర"],
        "Visakhapatnam": ["vizag", "visakhapatnam", "vishakapatnam", "vishakhapatnam", "విశాఖపట్నం", "వైజాగ్"],
        "Vijayawada": ["vijayawada", "bezawada", "విజయవాడ"],
        "Guntur": ["guntur", "గుంటూరు"],
        "Tirupati": ["tirupati", "tirupathi", "తిరుపతి"],
        "Nellore": ["nellore", "నెల్లూరు"],
        "Kakinada": ["kakinada", "కాకినాడ"],
        "Rajahmundry": ["rajahmundry", "rajamahendravaram"],
        "Kurnool": ["kurnool", "కర్నూలు"],
        "Anantapur": ["anantapur", "ananthapur"],
        "Amaravati": ["amaravati", "amaravathi"],
    },
}

# Places that put a person OUTSIDE the target geography when they say they live there.
ABROAD_PLACES = [
    "dubai", "uae", "u.a.e", "abu dhabi", "abudhabi", "sharjah", "ajman", "ras al khaimah", "emirates",
    "qatar", "doha", "saudi", "saudhi", "saudia", "ksa", "riyadh", "jeddah", "kuwait", "oman", "muscat", "bahrain", "gulf", "gcc",
    "usa", "america", "uk", "london", "canada", "toronto", "australia", "sydney", "melbourne",
    "singapore", "malaysia", "germany", "europe", "ireland", "netherlands", "new zealand", "sri lanka",
]
OTHER_INDIA_PLACES = [
    "mumbai", "bombay", "delhi", "new delhi", "ncr", "gurgaon", "gurugram", "noida", "pune", "kolkata",
    "ahmedabad", "surat", "jaipur", "lucknow", "chandigarh", "indore", "bhopal", "nagpur", "goa",
    "punjab", "gujarat", "maharashtra", "rajasthan", "haryana", "bihar", "odisha", "bhubaneswar",
    "patna", "thane", "navi mumbai", "vadodara", "ludhiana", "kanpur",
]

# Regional language -> state it most plausibly points to (WEAK evidence only).
LANG_STATE = {
    "ta": "Tamil Nadu", "ml": "Kerala", "kn": "Karnataka",
    "te": "Telangana / Andhra Pradesh",
}
LANG_NAME = {"ta": "Tamil", "ml": "Malayalam", "te": "Telugu", "kn": "Kannada"}
SCRIPT_RANGES = {"ta": (0x0B80, 0x0BFF), "te": (0x0C00, 0x0C7F), "kn": (0x0C80, 0x0CFF), "ml": (0x0D00, 0x0D7F)}

DUBAI = r"\bdubai\b|\buae\b|\bu\.a\.e\b|\bemirates\b|\bdxb\b|துபாய்|ദുബായ്|ദുബൈ|దుబాయ్|ದುಬೈ|ದುಬಾಯಿ"
PROPERTY = (
    r"\b(?:propert(?:y|ies)|real\s*estate|realty|apartments?|flats?|villas?|townhouses?|off[\s-]?plan|"
    r"studio|golden\s+visa|freehold|damac|emaar|sobha|danube|binghatti|azizi|nakheel|"
    r"home\s+(?:buy|purchase|loan)|rental\s+(?:yield|income)|mortgage)\b|\d\s?bhk\b|\bbhk\b"
    r"|வீடு|சொத்து|ரியல் எஸ்டேட்|ഫ്ലാറ്റ്|വീട്|പ്രോപ്പർട്ടി|റിയൽ എസ്റ്റേറ്റ്|ఇల్లు|ఫ్లాట్|ప్రాపర్టీ|రియల్ ఎస్టేట్|ಮನೆ|ಪ್ರಾಪರ್ಟಿ|ಫ್ಲಾಟ್"
)
# "invest in Dubai" style phrasing also counts as property context on property-focused sources
INVEST = r"\binvest(?:ing|ment|ments|or|ors)?\b|முதலீடு|നിക്ഷേപ|పెట్టుబడి|ಹೂಡಿಕೆ"

DUBAI_AREAS = (
    r"\b(?:jvc|jvt|jlt|jbr|jumeirah|business\s+bay|dubai\s+marina|downtown\s+dubai|dubai\s+hills|"
    r"dubai\s+south|dubai\s+creek|creek\s+harbour|palm\s+jumeirah|damac|emaar|sobha|danube|binghatti|"
    r"azizi|nakheel|meraas|ellington|samana|arjan|al\s+furjan|furjan|mbr\s+city|meydan|"
    r"international\s+city|silicon\s+oasis|dso|sports\s+city|motor\s+city|town\s+square|dubailand|"
    r"discovery\s+gardens|arabian\s+ranches|al\s+barsha|expo\s+city|damac\s+hills|damac\s+lagoons|"
    r"dubai\s+islands|emaar\s+south|the\s+valley|tilal\s+al\s+ghaf)\b"
)

AMOUNT = (
    r"(?:(?:₹|rs\.?|inr|aed|dhs?|usd|\$)\s?\d[\d,.]*\s?(?:k|l|lac|lacs|lakh|lakhs|cr|crs|crore|crores|m|mn|mil|million)?\b"
    r"|\d[\d,.]*\s?(?:k|l|lac|lacs|lakh|lakhs|cr|crs|crore|crores|m|mn|mil|million|aed|dirhams?|dhs|inr|rupees)\b"
    r"|\d{1,3}(?:,\d{2,3}){2,}"
    r"|\d[\d,.]*\s?(?:லட்சம்|கோடி|ലക്ഷം|കോടി|లక్షల|లక్ష|కోట్ల|కోటి|ಲಕ್ಷ|ಕೋಟಿ))"
)

# Each marker: list of regexes evaluated on lower-cased text.
_NOT_BUYING = r"(?:(?!sell|selling|rent|renting|tenant|tenants|lease|leasing|buyer|buyers)\w+\s+)"
PURCHASE = [
    r"\b(?:want|wanna|wana|whand|wnt|wants|wish|wishing|looking|planning|plan|plans|planned|interested|intend|intending|keen|"
    r"thinking|considering|hoping|decided|ready|trying|exploring|evaluating)\s+(?:\w+\s+){0,2}?"
    r"(?:to|in|of|on|about|for)?\s*(?:\w+\s+){0,2}?(?:buy|buying|purchase|purchasing|invest|investing|own|owning|book|booking)\b",
    r"\b(?:i|we)\s+need\s+to\s+(?:buy|invest|purchase)\b",
    r"\b(?:i|we)\s*(?:would|wud|'d)\s+(?:like|love)\s+to\s+(?:\w+\s+){0,2}?(?:buy|invest|purchase|book|own)\b",
    r"\bhow\s+(?:can|do|to|could|should)\s+(?:i|we|one|an?\s+indian|indians|nris?)?\s*(?:\w+\s+){0,2}?(?:buy|invest|purchase|book)\b",
    r"\b(?:can|could|shall|should)\s+(?:i|we|an?\s+indian|indians|indian\s+\w+)\s+(?:\w+\s+){0,2}?(?:buy|invest|purchase|get\s+(?:a\s+)?(?:loan|mortgage))\b",
    # "I want a 2BHK" - but not "I want to sell my flat" or "looking for a tenant for my apartment"
    r"\b(?:i|we)\s*(?:want|need|am\s+looking\s+for|are\s+looking\s+for|'m\s+looking\s+for|m\s+looking\s+for)\s+(?:a|an|one|1|2|3)?\s*" + _NOT_BUYING + r"{0,3}?(?:flat|apartment|villa|property|studio|house|home|bhk|townhouse)\b",
    r"\blooking\s+(?:for|at)\s+(?:a\s+|an\s+|some\s+)?" + _NOT_BUYING + r"{0,3}?(?:flat|apartment|villa|property|properties|studio|bhk|townhouse|investment|off[\s-]?plan)\b",
    r"\b(?:is|was)\s+(?:it|this|that|dubai|now)\s+(?:\w+\s+){0,3}?(?:worth|wise|sensible|good|advisable|smart|safe|right\s+time)\s+(?:\w+\s+){0,3}?(?:buy|buying|invest|investing)\b",
    # ---- romanised Tamil / Malayalam / Telugu / Kannada, as people actually type it ----
    r"\b(?:buy|invest|purchase)\s+pann(?:alam|alama|a\s+mudiyuma|a\s+poren|a\s+porom)\b",
    r"\b(?:vaanganum|vanganum|vaangalama|vangalama)\b|\bvaa?nga\s+mudiyuma\b",
    r"\binvest(?:ment)?\s+(?:possible|panna\s+mudiyum\w*|pannalam\w*|cheyyan\s+patt(?:umo|uo|o|um))\s*(?:a|ah|aa|o)?\b",
    r"\b(?:vaanganam|vanganam|medikkan|medikan|medikkanam)\b|\bvaa?ngan\s+(?:\w+\s+)?(?:kazhiyumo|pattumo|patto|agraham|aagraham)\b",
    r"\b(?:konali|konalani|konochu|konacha|konavachu)\b|\b(?:ela|ala|yela|etla)\s+(?:invest|buy|konali)\b",
    r"\b(?:kollabeku|tagobeku|togobeku)\b|\b(?:hege|hyage)\s+(?:invest|buy|kollodu|tagollodu)\b",
    # ---- native script: a property noun plus "to buy", or an explicit wish/ability form ----
    r"(?:வீடு|பிளாட்|ப்ளாட்|சொத்து|வில்லா|அபார்ட்மெண்ட்)\s*வாங்க(?![\u0bbe\u0bbf\u0bc1])|வாங்கணும்|வாங்க வேண்டும்|வாங்கலாமா|வாங்க முடியுமா|வாங்க விரும்ப|முதலீடு செய்ய",
    r"വാങ്ങാൻ|വാങ്ങണം|വാങ്ങാമോ|നിക്ഷേപിക്ക",
    r"కొనాలి|కొనాలని|కొనాలంటే|కొనవచ్చ|కొనుగోలు|పెట్టుబడి పెట్ట",
    r"ಖರೀದಿ|ಕೊಳ್ಳಬೇಕು|ತಗೊಳ್ಳ|ಹೂಡಿಕೆ ಮಾಡ",
]
# a native-script buying word followed by one of these is a denial ("cannot buy"), not intent
NATIVE_NEGATION = r"പറ്റില്ല|കഴിയില്ല|വേണ്ട|முடியாது|வேண்டாம்|கூடாது|కొనలేం|వద్దు|కుదరదు|ಬೇಡ|ಆಗಲ್ಲ|ಸಾಧ್ಯವಿಲ್ಲ"
BUDGET_WORD = r"\bbudget\b|பட்ஜெட்|ബജറ്റ്|బడ్జెట్|ಬಜೆಟ್"
# first-person capacity: "I have 80 lakhs", "we can invest 1 cr"
BUDGET_HAVE = r"\b(?:i|we)\s+(?:have|got|can\s+(?:invest|afford|spend|pay|arrange|put)|am\s+ready\s+with|are\s+ready\s+with)\b[^.?!\n]{0,40}?"
# a price ceiling that is asked about: "under 1 cr anything available?", "with 50 lakhs can I ...?"
BUDGET_ASK_PRE = r"\b(?:with|for|under|within|below|around|upto|up\s+to)\s+(?:of\s+|about\s+|a\s+)?"
BUDGET_ASK_POST = r"[^.!\n]{0,80}?(?:\?|\bcan\s+(?:i|we)\b|\bavailable\b|\bpossible\b|\bany\b|\bkedaikuma\b|\bkittumo\b|\bvastunda\b)"
TIMELINE = [
    r"\b(?:next|this|coming)\s+(?:year|month|quarter|\d+\s+months?|few\s+months|couple\s+of\s+(?:months|years))\b",
    r"\b(?:within|in)\s+(?:the\s+)?(?:next\s+)?(?:\d+|one|two|three|six|few|couple\s+of)\s*(?:-\s*\d+\s*)?(?:months?|years?|yrs?)\b",
    r"\bby\s+(?:20\d\d|jan\w*|feb\w*|mar\w*|apr\w*|jun\w*|jul\w*|aug\w*|sep\w*|oct\w*|nov\w*|dec\w*|end\s+of|next|early|mid|late)\b",
    r"\b(?:in|during|early|mid|late)\s+20(?:2[5-9]|3\d)\b",
]
REQUIREMENT = [
    r"\bstudio\b|\b\d\s*-?\s*(?:bhk|bed(?:room)?s?|br)\b|\b(?:one|two|three)[\s-]bed(?:room)?\b|\btownhouse\b|\bpenthouse\b",
    r"\boff[\s-]?plan\b|\bready\s+to\s+move\b|\bready\s+(?:property|apartment|unit|flat)\b|\bunder\s+construction\b",
    r"\bpayment\s+plan\b|\bdown\s*payment\b|\bpost[\s-]?handover\b|\bemi\b|\binstal?lments?\b",
    DUBAI_AREAS,
]
PROCESS = [
    r"\b(?:lrs|golden\s+visa|residen(?:ce|cy)\s+visa|investor\s+visa|fema|remit\w*|home\s+loan|mortgage|"
    r"bank\s+loan|title\s+deed|dld|oqood|service\s+charges?|rental\s+(?:yield|income|returns?)|roi|"
    r"return\s+on\s+investment|resale|capital\s+appreciation|freehold|tds|vat|"
    # tax only when it is about the property or the money moved, not "Germany has high tax"
    r"(?:property|rental|capital\s+gains?|income|inheritance)\s+tax\w*|tax[\s-]?free|"
    r"tax\w*\s+(?:on|for|in)\s+(?:the\s+)?(?:rent\w*|propert\w+|sale|resale|purchase|profits?|india|dubai|uae)|"
    r"documents?\s+(?:required|needed)|procedure|escrow)\b",
    # running costs and payment stages - what a buyer checks before committing
    r"\b(?:maint[ae]n[ae]nce)\s+(?:fees?|charges?|costs?)\b|\bservice\s+char\w+\b|\bhand\s?over\b|\bpossession\b",
    r"\badvance\b[^.?!\n]{0,40}\b(?:remaining|balance)\b",
]
COMPARISON = [
    r"\bvs\.?\b|\bversus\b|\bcompared?\s+(?:to|with)\b|\binstead\s+of\b|\brather\s+than\b",
    r"\bbetter\s+(?:than|to\s+(?:buy|invest)|option|investment)\b",
    r"\bwhich\s+(?:is|one|area|project|developer|location|builder|community)\s+(?:is\s+|would\s+be\s+)?(?:better|best|good)\b",
    r"\b(?:dubai|uae)\s+or\s+(?:india|bangalore|bengaluru|hyderabad|chennai|kochi|kerala|coimbatore)\b",
    r"\b(?:india|bangalore|bengaluru|hyderabad|chennai|kochi|kerala|coimbatore)\s+or\s+(?:dubai|uae)\b",
]
# Asking for the price, for details or for the seller's contact, or saying "interested".
# All of these are treated the same way: interest, but nothing to qualify on.
ENQUIRY = [
    r"\bint(?:e)?rested\b|\bmore\s+info\w*\b|\bbrochure\b|\bquotation\b",
    r"\bcontact\s+(?:number|no\.?|details?)\b|\b(?:phone|mobile|whatsapp)\s+(?:number|no\.?)\b|\byour\s+(?:number|contact)\b",
    r"\b(?:call|contact|whatsapp|dm|msg|message)\s+me\b|\bhow\s+(?:to|can\s+(?:i|we))\s+contact\b|\bdm\s+(?:pls|plz|please)\b|\b(?:pls|plz|please)\s+dm\b",
    r"\bstarting\s+(?:price|from)\b|\bminimum\s+(?:investment|amount|price)\b",
    # the same requests as people type them in one line: "pls number", "location?", "how to connect with you"
    r"\b(?:share|send|give|need|want|pls|plz|please|your|ur|what'?s)\s+(?:\w+\s+){0,2}?(?:number|whats\s?app|contact)\b",
    r"\bhow\s+(?:to|do\s+(?:i|we|people)|can\s+(?:i|we))\s+(?:connect|reach)\b|\bconnect\s+(?:me|with\s+(?:you|u))\b|\bstill\s+available\b",
    r"^\W*(?:(?:what\s+is\s+the\s+)?(?:exact\s+)?location|area|number|rate|amount)(?:\s+(?:bro|sir|pls|plz|please|madam|mam|ji))?\W*$",
]
# Words that name what is being asked for. On their own they prove nothing ("property prices went
# up", "wrong details"): they count as an enquiry only in a short question or request, or a comment of
# short comment, or when the word is the whole comment ("price", "details pls").
ENQUIRY_TOPIC = (r"\bdetails?\b|\bprice\b|\bcost\b(?!\s+of\s+living)|\bhow\s+much\b"
                 r"|\b(?:evlo|evalo|evvalavu|vilai|ethra|etra|eshtu|yestu)\b"
                 r"|(?<!கோ)விலை|விவரம்|விவரங்கள்|ஆர்வம்|വില(?!്ല)|വിശദാംശ|താല്പര്യ|താൽപ്പര്യ|ధర|వివరాలు|ఆసక్తి|ಬೆಲೆ|ವಿವರ|ಆಸಕ್ತಿ")
REQUEST_CUE = (r"\bwhat(?:'s|\s+is|\s+are)\b|\b(?:pls|plz|please|kindly|send|share|tell|give|need|want|know|sollunga|sollu|parayamo|parayu|"
               r"cheppandi|cheppu|heli|tharumo|tharamo|kudunga|ivvandi)\b")
ENQUIRY_MAX_WORDS = 15          # a request is short; a long text that happens to say "price" is commentary

# words that turn a mention of a buying topic into a question about it
# A real question: a question mark, a sentence that opens with a question word, or "how much"/"which"
# anywhere. "Housing fee is considered a tax" contains "is" but asks nothing.
QUESTION = (r"\?|(?:^|[.!\n]\s*)(?:how|what|which|when|where|can|could|is|are|does|do|will|would|should|any)\b"
            r"|\bhow\s+much\b|\bwhich\b|\b(?:evlo|evalo|evvalavu|ethra|etra|entha|eshtu|yestu)\b|எவ்வளவு|എത്ര|ఎంత|ಎಷ್ಟು"
            # "is there ...?", "will we get ...?" as typed without a question mark
            r"|\b(?:undo+|aano+|kittumo|kidumo|varumo|aakumo|pattumo|kazhiyumo|unda|untaya|untunda|vastunda|"
            r"irukka|irukkuma|kedaikuma|kidaikuma|mudiyuma|ideya|sigutta)\b")
BUYING_QUESTION_MAX_CHARS = 300        # a question is short; a long text using these words is commentary

# ---- disqualifiers ---------------------------------------------------------
AGENT = [
    r"\b(?:i\s*am|i'm|im|we\s*are|we're|myself)\s+(?!looking|searching|seeking|not\b|in\s+need|finding|interested|planning)"
    r"(?:a\s+|an\s+)?(?:\w+\s+){0,3}?(?:agent|broker|realtor|property\s+consultant|real\s+estate\s+consultant|"
    r"investment\s+advisor|channel\s+partner|sales\s+(?:manager|executive)|property\s+(?:dealer|advisor|expert))\b",
    r"\b(?:i|we)\s+work\s+(?:for|with|at|in)\s+(?:a\s+|an\s+)?(?:\w+\s+){0,3}?(?:brokerage|developer|real\s+estate|realty|agency)\b",
    r"\bas\s+(?:a|an)\s+(?:\w+\s+){0,2}?(?:agent|broker|realtor)\b",
    r"\bour\s+(?:team|company|agency|projects?|listings?|firm|office|experts?|services?|website|clients?|inventory)\b",
    r"\bwe\s+(?:offer|provide|deal|help|assist|specialis\w+|specializ\w+|are\s+(?:offering|providing|selling|launching))\b",
    r"\bi\s*(?:am|'m)\s+(?:in|into)\s+(?:the\s+)?real\s+estate\b",
    r"\bworking\s+(?:as\s+(?:a|an)\s+(?:\w+\s+){0,2}?(?:property|real\s*estate)\s+\w+|in\s+(?:\w+\s+){0,2}?real\s*estate)\b"
    r"|\breal\s*estate\s+lo\s+(?:job|work)\b|\bget\s+in\s+touch\s+with\s+me\b|\bif\s+you\s+need\s+any\s+(?:assistance|help)\b",
    r"\bwe\s+have\s+(?:\w+\s+){0,3}?(?:plots?|flats?|apartments?|villas?|projects?|properties|units|bhk)\b",
    # an advert phrased as a question: "Looking to invest in Dubai? Contact us today!"
    r"\b(?:contact|call|whatsapp|message|reach)\s+us\b|\bbest\s+deals?\b|\bi\s+have\s+a\s+client\b|\binterested\s+people\s+(?:message|call|contact|dm)\b",
    r"\b(?:looking|want|planning|interested)\s+to\s+(?:buy|invest)\b[^?\n]{0,60}\?\s*(?:call|contact|whatsapp|dm|message|reach)\b",
    # "DM for advice and enquiries" is a seller; "looking for advice" is a buyer
    r"\b(?:dm|call|contact|whatsapp|message)\b[^\n]{0,40}?\bfor\s+(?:advi[cs]e|enquir\w+|inquir\w+)\b"
    r"|\bfor\s+(?:advi[cs]e|enquir\w+|inquir\w+)\b[^\n]{0,40}?\b(?:dm|call|contact|whatsapp|message)\b"
    r"|\banyone\s+who\s+would\s+like\s+to\s+(?:know|invest|buy)\b",
    r"\bi\s+have\s+a\s+(?:\w+\s+){0,3}?deal\b|\b(?:you\s+can|u\s+can|please|pls)\s+dm\b(?!\s*(?:pls|please|me\s+(?:the|your)))",
    # self-description only: "I'm ... an investment advisor", never "recommend a real estate agent"
    r"\b(?:i\s*am|i'm|im|we\s+are|we're)\s+(?!looking|searching|seeking|not\b|in\s+need|finding|interested|planning|trying|hoping)"
    r"(?:\w+\s+){0,4}?an?\s+(?:investment|property|real\s+estate|mortgage)\s+(?:advisor|adviser|consultant|broker|agent)\b",
    r"\b(?:properties|realty|real\s+estate|estates?|developers?|brokers?|homes)\s+l\.?l\.?c\b|\bexpert\s+(?:help|guidance|advice)\s+from\b|\bjoin\s+\d+\+?\s|\b100%\s+guided\b|\bbook\s+(?:a\s+)?(?:free\s+)?(?:consultation|site\s+visit)\b",
    r"\bmy\s+clients?\b|\bi\s+(?:sell|sold|deal\s+in)\s+(?:\w+\s+){0,3}?(?:propert|apartment|unit|villa)",
    r"\b(?:dm|whatsapp|call|contact|ping|reach|message|msg|inbox|pm)\s+(?:me|us)\s+(?:for|to\s+(?:buy|invest|know|get|discuss))\b",
    r"\b(?:feel\s+free\s+to|happy\s+to|can)\s+(?:dm|pm|message|reach\s+out)\b|\bdm\s+(?:is\s+)?open\b|\bdrop\s+(?:me\s+)?a\s+(?:dm|message)\b",
    r"\bguaranteed\s+(?:returns?|roi|rental)\b|\bi\s+can\s+(?:help|assist|guide|connect)\s+you\b",
    r"\b(?:visit|check(?:\s+out)?)\s+(?:my|our)\s+(?:channel|profile|website|page|bio|listing)\b|\brera\s+(?:certified|registered|licensed)\b",
]
AGENT_NAME = (r"propert(?:y|ies)|realt(?:y|or|ors)|real[\s_-]*estate|estates?\b|developers?\b|consult\w+|"
              r"\bllc\b|\bpvt\b|\bltd\b|broker\w*|holdings|investments\b|homes\b")
# looking for a job - not a mortgage "salary" or a rental "vacancy"
JOB = (r"\b(?:any|need|want|looking\s+for|searching\s+for|get|find|give|provide|apply\s+for)\s+(?:\w+\s+){0,3}?(?:jobs?|work\s+visa|work\s+permit)\b"
       r"|\bjobs?\s+(?:vacanc\w+|openings?|opportunit\w+|offers?|irukk?a|kidaikk?uma|undo|unda|ide|ideya)\b|\b(?:resume|cv)\b|\bfresher\b|\bhiring\b|\boffer\s+letter\b")
# looking to rent a place - not an investor's "to rent out"
RENT = (r"\b(?:any|need|want|looking\s+for|available)\s+(?:\w+\s+){0,4}?(?:for|on)\s+rent\b|\b(?:want|need|looking)\s+to\s+rent\s+(?:a|an)\b"
        # "2bhk rent evlo?", "studio monthly rent how much", "1bhk for rent in JVC?", "safe for bachelors to stay?"
        r"|(?:bhk|\bstudio|\broom|\bflat|\bapartment|\bvilla)\s+(?:monthly\s+|yearly\s+)?rent\b(?!\s*(?:out|al\b|yield|income|return))"
        r"|\b(?:monthly|yearly)\s+rent\b|\bfor\s+rent\b|\bbachelors?\b|\bto\s+stay\b"
        r"|\brental\s+(?:accommodation|room)\b|\bbed\s*space\b|\broom\s+(?:rent|sharing)\b|\blooking\s+(?:for\s+)?(?:a\s+)?(?:room|roommate|flatmate)\b")
# first person only: "he is a sales guy trying to sell" is about someone else
SELL = (r"\b(?:i|we|i'm|im|i\s+am|we\s+are)\s+(?:\w+\s+){0,2}?(?:want|need|looking|planning|wish|trying)\s+to\s+sell\b"
        r"|\bselling\s+my\b|\bsell\s+my\b")
SKEPTIC = (r"\b(?:scam\w*|fraud\w*|bubble|crash\w*|don'?t\s+(?:buy|invest)|do\s+not\s+(?:buy|invest)|never\s+(?:buy|invest)|"
           r"worst|waste\s+of|fake|trap|oversupply|beware|lost\s+(?:my\s+|all\s+)?money|stay\s+away|avoid)\b")
# "I bought a flat there": an existing owner is an investor worth validating, not noise
OWNER_INVESTOR = (r"\b(?:i|we)\s+(?:have\s+|had\s+|'ve\s+)?(?:already\s+|recently\s+|just\s+)?(?:bought|purchased|booked|own|invested\s+in)\s+"
                  r"(?:\w+\s+){0,4}?(?:flats?|apartments?|villas?|propert(?:y|ies)|studio|units?|townhouse|bhk|there|in\s+dubai|in\s+uae)\b")
ADVICE_GIVER = r"\b(?:you\s+should|(?<!if )you\s+can|you\s+need\s+to|you'?ll|my\s+advice|i\s+would\s+suggest|i'?d\s+suggest|i\s+suggest|trust\s+me|pro\s+tip)\b"

# A link is seller language only together with a plug for the author's own or a "found" product.
PROMO_WITH_LINK = (r"\bi\s+(?:built|made|created|launched|run|write)\s+(?:a|an|this|the)\b"
                   r"|\b(?:site|website|platform|tool|app|newsletter|channel|group)\s+(?:i\s+found\s+)?called\b"
                   r"|\b(?:check\s+(?:it\s+)?out|sign\s+up|subscribe|join\s+(?:our|my|the)|survey)\b")

# A buying phrase only counts when the speaker is the subject: "if you want to invest",
# "residents planning to buy", "people who want to buy" are not the author's own intent.
# things people say they want to buy in Dubai that are not property
NOT_PROPERTY = (r"\b(?:gold|car|cars|bike|tickets?|flights?|phone|iphone|laptop|merch\w*|merchandise|shares?|stocks?|crypto|bitcoin|"
                r"burj\s+khalifa|channel|course|watch|perfume)\b")
NOT_FIRST_PERSON = (r"\b(?:you|u|ur|they|people|those|anyone|someone|somebody|who|indians|investors|residents|buyers|nris?|"
                    r"he|she|everyone|everybody|nobody|others|clients?|customers?|friends?|persons?|guys?|party|"
                    r"brother|sister|father|mother|uncle|cousin|wife|husband|son|daughter|parents|relatives?)\s+(?:\w+\s+){0,2}$"
                    r"|\b(?:no|not|don'?t|never|cannot|can'?t|won'?t|didn'?t)\s+(?:\w+\s+){0,2}$")

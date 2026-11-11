# Dubai Property Prospect Workflow — South India

A re-runnable workflow that looks for people in **Karnataka, Kerala, Tamil Nadu, Telangana and Andhra Pradesh**
who have publicly shown interest in **buying or investing in Dubai property**, classifies each one as
`strong_signal`, `needs_validation` or `reject` with a written reason, and exports the result to a sheet.

It reads public comments only, contacts nobody, and removes phone numbers, e-mail addresses and links before
anything is stored.

## Result at a glance

Run of 11 November 2026, YouTube only.

| | Count |
|---|---|
| Candidates discovered | **218** |
| Meet both tests in their own words (buying interest and a South India home they state) | **2** |
| Strong signal | **0** |
| Needs validation | **27** |
| Rejected | **191** |

**Two people genuinely qualify on both tests, and neither reaches the strong-signal bar.** The other 25 in
"needs validation" show buying interest in their own words, but nothing they wrote says where they live: they
are linked to South India only by the language of the video they commented on. This is a working method and a
short list worth a first look, not a list of leads.

| Deliverable | Where |
|---|---|
| Results sheet | [`output/prospects.xlsx`](output/prospects.xlsx) (tabs) · [`output/prospects_all.csv`](output/prospects_all.csv) |
| Shortlist of five | [`output/shortlist_top5.csv`](output/shortlist_top5.csv) |
| Run summary | [`output/summary.md`](output/summary.md) · [`output/run_manifest.json`](output/run_manifest.json) |
| Full rules, columns, settings, troubleshooting | [`docs/DETAILS.md`](docs/DETAILS.md) |
| Dashboard | https://claude.ai/artifact/Uym8RXvyBU5hTYemzAof6r (opens only for people it has been shared with) |

## The short explanation

**Sources.** Public comments under YouTube videos about buying Dubai property, read through the official
YouTube Data API v3. Videos in Tamil, Malayalam, Telugu or Kannada are read up to 2,000 comment threads each,
with the first few replies of each thread;
on the most-commented Dubai-property videos in any language, only comments that name a South India place are
read. Sites that need a login, charge for access or block scripts (LinkedIn, Facebook, Instagram, X, Quora,
reddit.com) were not used and not worked around.

**Qualification rules.** A person must pass two separate tests: buying intent in their own words, and a link to
South India.

| Status | Rule |
|---|---|
| `strong_signal` | A wish to buy plus a specific (budget, timeline, requirement, comparison or process question), a South India home they state themselves, and a signal under 18 months old. |
| `needs_validation` | Intent in their own words (a wish to buy, a budget, a buying question, or a past purchase by someone who states a South India home) with something still missing, usually the location. |
| `reject` | Sellers and agents; renters; requests for only a price, details or a contact with no stated location; replies to other viewers; job-seekers and critics; anyone who says, or whose channel declares, they live outside South India; comments under a video that is not about Dubai. |

A job title, wealth or a location on its own never qualifies anyone. The full rules are in
[`docs/DETAILS.md`](docs/DETAILS.md).

**Discovered versus qualified.** 3,226 comments from 2,612 people → **218 candidates** → **27 need validation**,
of whom **2 meet both tests**; 0 strong signal; 191 rejected.

**Limitations.**

- **Location is the weak link.** Only 2 of the 27 say where they live (both Chennai). For the rest the only
  link is the video's language, and a Tamil or Malayalam speaker may well live in the Gulf: of the candidates
  whose channel declares a country, about half declare one outside India.
- **Evidence per person is thin.** Most rows are one short comment. Identity, finances and residence are
  unverified and listed per row.
- **Concentrated source.** YouTube only. 96 of the 218 candidates come from one channel and 130 from three
  videos. No one is linked to Karnataka.
- **Keyword rules miss regional-language buyers.** Against an independent read they found fewer than half of
  the people showing buying intent. Six of the 27 were added by a recorded review decision.
- **Built with an AI coding assistant**, as the brief allows, including the review decisions. They are one
  reviewer's judgement and have not been checked by a speaker of these languages.

## How it works

```mermaid
flowchart TD
    A["YouTube Data API<br/>54 searches for Dubai-property videos"] --> B["Keep videos about Dubai property<br/>in Tamil, Malayalam, Telugu or Kannada"]
    B --> C["Read public comments<br/>3,226 comments from 2,612 people"]
    C --> D["Clean and redact<br/>phones, e-mails, links removed"]
    D --> E["One record per person<br/>2,173 with a comment in scope"]
    E --> F{"Did they ask or say something<br/>a seller could act on?"}
    F -->|"No: 1,928 people, plus 27 video creators"| X["Removed as irrelevant<br/>counted, not listed"]
    F -->|Yes| G["218 candidates"]
    G --> H["Score buying intent and South India evidence<br/>look up the country each channel declares"]
    H --> I["Automatic status and reason"]
    I --> J["Review decisions, recorded in files<br/>each addition must quote the comment"]
    J --> K["0 strong signal"]
    J --> L["27 needs validation<br/>2 meet both tests"]
    J --> M["191 rejected"]
    K --> N["Export: CSV, XLSX, shortlist, summary, manifest"]
    L --> N
    M --> N
```

| Step | File |
|---|---|
| Discover and read comments | [`prospector/sources/youtube.py`](prospector/sources/youtube.py) |
| Redaction, intent markers, location evidence | [`prospector/textsig.py`](prospector/textsig.py), patterns in [`prospector/lexicon.py`](prospector/lexicon.py) |
| One record per person, status and reason | [`prospector/qualify.py`](prospector/qualify.py) |
| Processing order, review decisions, shortlist | [`prospector/pipeline.py`](prospector/pipeline.py) |
| CSV, XLSX, summary, manifest | [`prospector/export.py`](prospector/export.py) |
| Optional AI reading stage (off by default, not used for these results) | [`prospector/ai_reader.py`](prospector/ai_reader.py) |

## Setup guide

Everything needed is free. Allow about ten minutes.

**You need:** Python 3.10 or newer (developed on 3.13), Git, and a Google account for the free API key.

**1. Get the code and install the two dependencies.**

```bash
git clone https://github.com/MINTU296/dubai-prospect-workflow
```

```bash
cd dubai-prospect-workflow
```

```bash
pip install -r requirements.txt
```

A virtual environment is optional: `python3 -m venv .venv` then `source .venv/bin/activate` (on Windows,
`py -m venv .venv` then `.venv\Scripts\Activate.ps1`).

**2. Create a YouTube Data API key.**

1. In the [Google Cloud Console](https://console.cloud.google.com/projectcreate), create a project.
2. On the [YouTube Data API v3 page](https://console.cloud.google.com/apis/library/youtube.googleapis.com),
   click **Enable**.
3. Under [Credentials](https://console.cloud.google.com/apis/credentials), choose
   **Create credentials → API key** and copy it.

**3. Give the key to the workflow.** Copy the template and paste the key after the `=` sign:

```bash
cp .env.example .env
```

```text
YOUTUBE_API_KEY=paste-your-key-here
```

`.env` is ignored by git. An environment variable of the same name also works and takes precedence.

**4. Run it.**

```bash
python run.py
```

A first run takes a few minutes and uses about 6,700 of the 10,000 free daily quota units. It writes five files
to `output/`. To view the sheet in Google Sheets, choose **File → Import → Upload** and select
`prospects.xlsx`.

**5. Check the installation (optional).**

```bash
pip install -r requirements-dev.txt
```

```bash
python -m pytest tests -q
```

225 tests pass and one is skipped (it needs the optional `anthropic` package); none needs a key or the network.

| Command | What it does |
|---|---|
| `python run.py` | Collect, qualify, export. Reuses cached answers under 24 hours old. |
| `python run.py --offline` | Re-qualify from your local cache: no network, no quota. |
| `python run.py --refresh` | Ignore the cache and fetch again. |
| `python run.py --as-of 2026-11-11` | Make freshness decisions as of a given date. |
| `python run.py --find "some words"` | Show the id and status of everyone whose comment contains the words. |
| `python run.py --purge-cache` | Delete all cached public text. |
| `python run.py --help` | Every option, and the exit codes. |

**Re-runnable, not byte-reproducible.** The cache is not in the repository and YouTube's search results change,
so a fresh run finds a somewhat different set of people. The committed `output/` reproduces exactly from the
author's cache; `run_manifest.json` records the commit, settings and checksums.

## Results

| Funnel step | Count |
|---|---|
| Public comments read | 3,226 |
| People who wrote them | 2,612 |
| People with a comment about Dubai property | 2,173 |
| Video creators' own comments removed | 27 |
| Removed as irrelevant (asked nothing, no wish to buy) | 1,928 |
| **Candidates discovered** | **218** |
| `strong_signal` | **0** |
| `needs_validation` | **27** |
| ...of whom meet both tests in their own words | **2** |
| `reject` | **191** |

**The 27 who need validation.** Eleven say they want to buy or invest (two state an amount: 25 lakh and
3 crore), one says he already bought and lives in Chennai, and fifteen asked a buying question such as "How
much down payment?". Twenty-one were found by the rules and six by a review decision. Location: two state
Chennai, one names a Hyderabad locality without calling it home, and 24 are linked only by video language
(Tamil 16, Telugu 4, Malayalam 4). Fourteen of the 27 commented on one Tamil realtor's channel.

**The 191 rejected.**

| Reason | Count |
|---|---|
| Only asked for a price, details or a contact, and gave no location | 132 |
| Commented under a video that is about a villa in Ajman, not Dubai | 18 |
| Seller or agent, by what they wrote (7) or by a business-name handle (6) | 13 |
| Replied to another viewer rather than the creator | 7 |
| Rejected by a review decision | 9 |
| Channel declares a country outside India | 5 |
| Says they live elsewhere, owner with no sign of buying again, advice-giver, critic, job-seeker, no South India link | 7 |

**The shortlist.** Ranked by a stated wish to buy and its specifics, then by location the person states
themselves. Only the first and third meet both tests; the second names a Hyderabad locality but does not say
he lives there; the last two are located only by video language. Only the first shows both a wish to buy
now and a stated home; the third is an existing owner, not someone who says he is buying again.

**Why nobody reaches strong signal.** It needs a wish to buy, a specific, and a stated South India home in the
same public record. People who comment on these videos ask one short question and rarely say where they live.
Three further checks for location were measured and found nearly empty: the country a channel declares (17 of
218 declare one), the channel description (3 candidates named a South India place, all three rejected for
other reasons), and an independent read of every comment for a stated home (10 found, none with buying
intent).

## What was checked

- **Independent read.** Six AI readers labelled 1,552 commenters (the data at the time) without seeing the
  rules' verdicts, quoting the comment for every label. The rules had found 34 of the 79 people in whom the
  readers saw buying intent. General rules were added for the gaps that generalise.
- **Two independent reviews** of the results and the code then found real faults, now fixed:
  - about a quarter of the rows then listed as needing validation did not survive a strict read, including
    several added by review decision, and one source video was about Ajman, not Dubai;
  - the classifier let a renter or a seller with a budget through as a strong signal, and rejected buyers who
    named Dubai as where the flat is ("naan Dubai la oru 2BHK vaanganum") as if they lived there;
  - the shortlist ranked an existing owner above people with a budget, a timeline or a comparison;
  - the README called 46 people "qualified" when two met both tests.

  Every input those reviews found misclassified is now a test.
- **Not checked.** No speaker of Tamil, Malayalam, Telugu or Kannada has read the regional-language rows. The
  roughly 600 commenters added by the last run were not part of the independent read. The optional AI reading
  stage has never been run against the live API.

## Privacy and compliance

- **Redaction.** Phone numbers, e-mail addresses, links and handles on other platforms are replaced by tokens
  before anything is cached or exported, in comment text, display names, and video titles, descriptions and
  tags. It is pattern-based and will miss unusual formats. A @mention of another YouTube user inside a comment
  is kept, because it is part of the public comment.
- **Minimal lookups.** For a candidate's channel only the declared country code is requested and cached.
- **Retention.** Cached text older than 30 days is deleted on the next online run; `--purge-cache` deletes it
  at once. The committed `output/` holds 218 public handles with a judgement against each, exists for this
  evaluation only, and should be deleted afterwards.
- **Removal on request.** A row with status `exclude` in `review/manual_review.csv` removes that person from
  every output.
- **Read-only.** Nothing is posted and nobody is messaged. The API key is sent in a header and never logged.
- **Open question.** Compiling commenters' handles into a prospect list may sit uneasily with YouTube's API
  developer policies. I have not resolved that; it should be checked before any real use.

## Next steps

1. A consented validation step, such as a form linked from a developer's own channel, before any record is
   treated as a lead. It is also the only way to establish residence.
2. Have a speaker of each language read the regional-language rows.
3. Run the AI reading stage against the live API and compare it with the independent read.
4. More Kannada and Telugu sources; the current ones are thin.

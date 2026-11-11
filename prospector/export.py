"""CSV / XLSX / summary / manifest export.

- Files are written to a temporary name and renamed, so a failed run never leaves a
  half-written sheet where a good one was.
- Every cell is neutralised against spreadsheet formula injection: comment text and
  display names are attacker-controlled input.
"""
import csv
import hashlib
import json
import logging
import os
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import config
from prospector.pipeline import OVERRIDE_STATUSES
from prospector.qualify import COLUMNS, READ_MARKER, REVIEW_SPECIFICS, to_row, valid_review_signal

log = logging.getLogger("prospector.export")

# A cell that starts with = + - tab/CR is read as a formula by Excel and Sheets; so is a
# leading @ unless it is just a plain "@handle".
_FORMULA = re.compile(r"^[=+\-\t\r]|^@(?![^\s()=+*/!,;'\"]+$)")       # any-script @handle is fine


def safe_cell(v):
    """Neutralise a value for CSV: a leading apostrophe makes spreadsheets treat it as text."""
    return "'" + v if isinstance(v, str) and _FORMULA.search(v) else v


def load_overrides(path):
    """review/manual_review.csv -> {prospect_id: {status, note, signal}}. Missing file = no overrides.

    The optional `signal` column (wants_to_buy, buying_question or already_bought, optionally with
    +budget, +timeline, +comparison or +requirement) records what the reviewer read in a comment
    no keyword rule matched, and `quote` is the exact text it rests on.

    Rows with an unknown status or no id are skipped with a warning, never fatal.
    """
    path = Path(path)
    if not path.exists():
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            pid, status = (r.get("prospect_id") or "").strip(), (r.get("status") or "").strip()
            if not pid and not status:
                continue
            if not pid or status not in OVERRIDE_STATUSES:
                log.warning("%s line %d ignored: need a prospect_id and a status in %s", path.name, n, OVERRIDE_STATUSES)
                continue
            signal = (r.get("signal") or "").strip()
            if signal and not valid_review_signal(signal):
                log.warning("%s line %d: unknown signal %r ignored (use one of %s, optionally followed by +%s)",
                            path.name, n, signal, sorted(READ_MARKER), " +".join(REVIEW_SPECIFICS))
                signal = ""
            out[pid] = {"status": status, "note": (r.get("note") or "").strip() or "no note given", "signal": signal,
                        "quote": (r.get("quote") or "").strip()}
    return out


def load_video_review(path):
    """review/video_review.csv -> {video_id: note} for videos a reviewer found are not about Dubai property."""
    path = Path(path)
    if not path.exists():
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            vid, decision = (r.get("video_id") or "").strip(), (r.get("decision") or "").strip()
            if not vid and not decision:
                continue
            if not vid or decision != "off_target":
                log.warning("%s line %d ignored: need a video_id and the decision off_target", path.name, n)
                continue
            out[vid] = (r.get("note") or "").strip() or "marked off-target on review"
    return out


def _atomic(path, write):
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        write(tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _csv(path, rows, columns):
    def write(tmp):
        with open(tmp, "w", newline="", encoding="utf-8-sig") as f:   # BOM so Excel/Sheets read regional scripts
            w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({c: safe_cell(r.get(c, "")) for c in columns})
    _atomic(path, write)


def _xlsx(path, sheets):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        log.warning("openpyxl is not installed - %s was not written (CSV files are complete)", Path(path).name)
        return False
    wb = Workbook()
    wb.remove(wb.active)
    for name, (columns, rows) in sheets.items():
        ws = wb.create_sheet(name[:31])
        ws.append(columns)
        for c in ws[1]:
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3A5F")
        for r in rows:
            ws.append([r.get(c, "") for c in columns])
        ws.freeze_panes = "A2"
        for i, c in enumerate(columns):
            wide = c in ("evidence_of_interest", "qualification_reason", "location_evidence", "unverified_information")
            ws.column_dimensions[ws.cell(1, i + 1).column_letter].width = 60 if wide else 22
        for row in ws.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, str):
                    c.data_type = "s"          # always a string cell: "=..." must never become a formula
                c.alignment = Alignment(wrap_text=True, vertical="top")
    _atomic(path, lambda tmp: wb.save(tmp))
    return True


def _git(root, *args):
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _git_state(root):
    """(commit, True if code files differ from that commit). Outputs themselves are ignored."""
    commit = _git(root, "rev-parse", "--short", "HEAD") or None
    dirty = bool(_git(root, "status", "--porcelain", "--", ".", ":!output"))
    return commit, dirty


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).exists() else None


def write_all(candidates, shortlist, funnel, out_dir, as_of=None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    as_of = as_of or config.TODAY
    rows = [to_row(p) for p in candidates]
    top = [dict(rank=i + 1, **to_row(p)) for i, p in enumerate(shortlist)]
    _csv(out / "prospects_all.csv", rows, COLUMNS)
    _csv(out / "shortlist_top5.csv", top, ["rank"] + COLUMNS)
    by = lambda s: [r for r in rows if r["qualification_status"] == s]
    frows = [{"metric": k, "value": "; ".join(v) if isinstance(v, list) else str(v)} for k, v in funnel.items()]
    wrote_xlsx = _xlsx(out / "prospects.xlsx", {
        "Top 5 shortlist": (["rank"] + COLUMNS, top),
        "All candidates": (COLUMNS, rows),
        "Strong signal": (COLUMNS, by("strong_signal")),
        "Needs validation": (COLUMNS, by("needs_validation")),
        "Rejected": (COLUMNS, by("reject")),
        "Funnel": (["metric", "value"], frows),
    })

    reasons = Counter(r["qualification_reason"].split(" To validate")[0][:95] for r in by("reject"))
    states = Counter((r["state"] if r["state"] != "unknown" else "unknown - inferred: " + (r["inferred_region"] or "none"))
                     for r in rows if r["qualification_status"] != "reject")
    lines = [f"# Run summary (as of {as_of})", "", "| Funnel step | Count |", "|---|---|"]
    skip = ("api_calls", "quota_units", "cache_hits")       # run mechanics, not results
    lines += [f"| {k.replace('_', ' ')} | {v} |" for k, v in funnel.items()
              if not isinstance(v, list) and not k.endswith(skip)]
    for k, v in funnel.items():
        if isinstance(v, list) and v:
            lines += ["", f"### {k.replace('_', ' ').capitalize()} ({len(v)})", ""] + [f"- {x}" for x in v]
    lines += ["", "## Qualified + to-validate prospects by state", ""] + [f"- {k}: {v}" for k, v in states.most_common()]
    lines += ["", "## Why records were rejected", ""] + [f"- {v} x {k}" for k, v in reasons.most_common()]
    lines += ["", "## Top 5", ""]
    for r in top:
        where = f"{r['city']}, {r['state']}" if r["state"] != "unknown" else "location unknown" + (f"; inferred {r['inferred_region']}" if r["inferred_region"] else "")
        lines += [f"{r['rank']}. **{r['public_name_or_handle']}** ({r['qualification_status']}) - {where} - {r['signal_date']}  ",
                  f"   {r['source_link']}  ", f"   > {r['evidence_of_interest']}", ""]
    _atomic(out / "summary.md", lambda tmp: Path(tmp).write_text("\n".join(lines), encoding="utf-8"))

    # Audit trail: what produced this sheet, and checksums to detect later edits.
    files = ["prospects_all.csv", "shortlist_top5.csv", "summary.md"] + (["prospects.xlsx"] if wrote_xlsx else [])
    commit, dirty = _git_state(Path(__file__).resolve().parent.parent)
    if dirty:
        log.warning("code has uncommitted changes - the manifest's commit does not fully describe this run")
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": as_of,
        "code_commit": commit,
        "code_had_uncommitted_changes": dirty,
        "settings": {k: getattr(config, k) for k in ("SIGNAL_AFTER", "FRESH_MONTHS", "CANDIDATE_CAP", "CACHE_TTL_HOURS",
                                                     "CACHE_RETENTION_DAYS")},
        "sources": sorted({r["platform"] for r in rows}),
        "counts": {k: v for k, v in funnel.items() if not isinstance(v, list)},
        "sha256": {f: _sha256(out / f) for f in files if f != "prospects.xlsx"},   # xlsx embeds a timestamp
    }
    _atomic(out / "run_manifest.json", lambda tmp: Path(tmp).write_text(json.dumps(manifest, indent=2), encoding="utf-8"))
    return rows

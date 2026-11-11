"""Small, safe on-disk JSON cache shared by the collectors.

Guarantees:
- writes are atomic (temp file + rename), so an interrupted run never leaves a
  half-written file behind;
- a corrupt file is treated as a cache miss and removed, never a crash;
- entries can expire (TTL) and are deleted after a retention period.
"""
import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path

log = logging.getLogger("prospector.cache")


def read_json(path):
    """Parsed JSON, or None if the file is missing or unreadable (corrupt files are removed)."""
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        log.warning("corrupt cache file %s removed (%s)", path.name, e)
        try:
            path.unlink()
        except OSError:
            pass
        return None


def write_json_atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}.tmp")   # unique per writer
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def is_fresh(path, ttl_hours):
    """True if the file exists and is younger than ttl_hours (None = never expires)."""
    try:
        age = time.time() - Path(path).stat().st_mtime
    except OSError:
        return False
    return ttl_hours is None or age < ttl_hours * 3600


def purge(directory, max_age_days):
    """Delete cached responses older than max_age_days (data-retention limit). Returns count."""
    directory, n = Path(directory), 0
    if not directory.exists() or max_age_days is None:
        return 0
    cutoff = time.time() - max_age_days * 86400
    for f in directory.rglob("*"):
        if f.is_file() and (f.suffix in (".json", ".tmp")) and f.stat().st_mtime < cutoff:
            try:
                f.unlink()
                n += 1
            except OSError:
                pass
    return n

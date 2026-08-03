"""Append-only job store.

One NDJSON file per month under data/, one record per line. Appends give git clean diffs,
which a rewritten SQLite file would not — at six collections a day that is the difference
between a repo that stays small and one that grows by megabytes daily.

The record shape is the same regardless of which board a job came from:

    id             source-scoped stable key      "gh:spacex:8643277002"
    url_key        normalized url, the dedupe key across sources
    source         simplify | greenhouse | ashby | lever | workday
    company, title, locations, category, url
    posted_at      what the source claims; unreliable (Workday only says "30+ Days Ago")
    first_seen_at  when WE saw it. Trustworthy, and what every "what's new" query uses.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
WATERMARK = DATA_DIR / "watermark.json"


def _month_file(ts):
    return DATA_DIR / f"jobs-{datetime.fromtimestamp(ts, timezone.utc):%Y-%m}.ndjson"


def url_key(url):
    """Dedupe key. The same job reaches us from Simplify and from the company board under
    different ids and different tracking params, so key on host+path alone."""
    u = re.sub(r"^https?://(www\.)?", "", (url or "").strip().lower())
    return u.split("?")[0].split("#")[0].rstrip("/")


def files():
    return sorted(DATA_DIR.glob("jobs-*.ndjson"))


def read_all():
    for path in files():
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)


def known_keys():
    return {r["url_key"] for r in read_all()}


def append(records, ts):
    """Write records to the current month's file. Caller has already deduped."""
    if not records:
        return 0
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _month_file(ts)
    with path.open("a") as fh:
        for r in records:
            fh.write(json.dumps(r, separators=(",", ":")) + "\n")
    return len(records)


def read_since(ts):
    """Everything first seen after ts, oldest sighting first so a backlog drains in order."""
    return sorted((r for r in read_all() if r.get("first_seen_at", 0) > ts),
                  key=lambda r: r["first_seen_at"])


def get_watermark():
    if not WATERMARK.exists():
        return 0
    return json.loads(WATERMARK.read_text()).get("last_email_at", 0)


def set_watermark(ts):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WATERMARK.write_text(json.dumps({"last_email_at": int(ts)}, indent=1) + "\n")

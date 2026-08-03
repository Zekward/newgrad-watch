#!/usr/bin/env python3
"""Fetch every source, normalize, append anything new to the store. Sends no email.

Runs every four hours. Keeping this separate from the mailer means a flaky job board can
never cost you a digest, and a digest can be re-sent without re-fetching anything.
"""

import argparse
import json
import sys
import time
import urllib.request

import sources
import store

SIMPLIFY_URL = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"
CATEGORIES = {"Software", "AI/ML/Data", "Quant"}
MAX_AGE_DAYS = 7


def fetch_simplify():
    req = urllib.request.Request(SIMPLIFY_URL, headers={"User-Agent": "newgrad-watch"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def simplify_relevant(job, now):
    return (job.get("active") and job.get("is_visible")
            and job.get("category") in CATEGORIES
            and now - job.get("date_posted", 0) <= MAX_AGE_DAYS * 86400)


def to_record(job, source, now):
    return {
        "id": job.get("id"),
        "url_key": store.url_key(job.get("url")),
        "source": source,
        "company": job.get("company_name"),
        "title": job.get("title"),
        "locations": job.get("locations") or [],
        "category": job.get("category"),
        "url": job.get("url"),
        "posted_at": int(job.get("date_posted") or now),
        "first_seen_at": int(now),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-simplify", action="store_true", help="direct boards only")
    ap.add_argument("--dry-run", action="store_true", help="report what would be added, write nothing")
    args = ap.parse_args()

    now = time.time()
    candidates = []

    if not args.skip_simplify:
        feed = fetch_simplify()
        rows = [j for j in feed if simplify_relevant(j, now)]
        print(f"  simplify: {len(rows)} relevant of {len(feed)}")
        candidates += [to_record(j, "simplify", now) for j in rows]

    for row in sources.fetch_all(now):
        candidates.append(to_record(row, row.get("board", "direct"), now))

    # Dedupe within this batch first — the same job legitimately arrives from Simplify and
    # from the company's own board in the same run.
    seen, fresh = store.known_keys(), []
    for r in candidates:
        if not r["url_key"] or r["url_key"] in seen:
            continue
        seen.add(r["url_key"])
        fresh.append(r)

    print(f"  {len(candidates)} fetched, {len(fresh)} new")
    if args.dry_run:
        for r in fresh[:10]:
            print(f"    {r['company']} — {r['title'][:52]}")
        return 0

    store.append(fresh, now)
    print(f"stored {len(fresh)} new postings")
    return 0


if __name__ == "__main__":
    sys.exit(main())

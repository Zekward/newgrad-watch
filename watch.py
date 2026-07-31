#!/usr/bin/env python3
"""Email new postings from the SimplifyJobs New-Grad-Positions feed.

Fetches the upstream listings.json, keeps the rows that are active and recent,
diffs them against state/seen.json, and emails whatever is new.
"""

import argparse
import html
import json
import os
import smtplib
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

FEED_URL = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json"
STATE_PATH = Path(__file__).resolve().parent / "state" / "seen.json"
MAX_AGE_DAYS = 30
CATEGORIES = {"Software", "AI/ML/Data", "Quant"}


def fetch_feed():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "newgrad-watch"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


def is_relevant(job, now):
    return (
        job.get("active")
        and job.get("is_visible")
        and job.get("category") in CATEGORIES
        and now - job.get("date_posted", 0) <= MAX_AGE_DAYS * 86400
    )


def load_seen():
    if not STATE_PATH.exists():
        return None
    return set(json.loads(STATE_PATH.read_text()))


def save_seen(ids):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(sorted(ids), indent=0) + "\n")


def render(jobs):
    """Return (plain_text, html) for the new-jobs digest."""
    jobs = sorted(jobs, key=lambda j: (j["company_name"].lower(), j["title"].lower()))
    lines, rows = [], []
    for j in jobs:
        where = ", ".join(j.get("locations") or []) or "—"
        posted = datetime.fromtimestamp(j["date_posted"], timezone.utc).strftime("%b %d")
        lines.append(f"{j['company_name']} — {j['title']}\n  {where} · {j['category']} · posted {posted}\n  {j['url']}\n")
        rows.append(
            "<tr>"
            f"<td style='padding:8px 12px 8px 0;vertical-align:top'><b>{html.escape(j['company_name'])}</b></td>"
            f"<td style='padding:8px 0'><a href='{html.escape(j['url'])}'>{html.escape(j['title'])}</a>"
            f"<div style='color:#666;font-size:13px'>{html.escape(where)} · {html.escape(j['category'])} · posted {posted}</div></td>"
            "</tr>"
        )
    body_html = (
        "<div style='font-family:-apple-system,Segoe UI,sans-serif;font-size:14px'>"
        f"<p>{len(jobs)} new posting{'s' if len(jobs) != 1 else ''}.</p>"
        f"<table style='border-collapse:collapse'>{''.join(rows)}</table>"
        "<p style='color:#888;font-size:12px'>Source: SimplifyJobs/New-Grad-Positions</p></div>"
    )
    return "\n".join(lines), body_html


def fake_jobs(now):
    """Three obviously-fake postings, for verifying delivery end to end."""
    return [
        {
            "company_name": "Fake Corp",
            "title": "Software Engineer, New Grad",
            "locations": ["San Francisco, CA", "Remote"],
            "category": "Software",
            "url": "https://example.com/fake-job-1",
            "date_posted": now,
        },
        {
            "company_name": "Test Industries",
            "title": "Machine Learning Engineer I",
            "locations": ["New York, NY"],
            "category": "AI/ML/Data",
            "url": "https://example.com/fake-job-2",
            "date_posted": now,
        },
        {
            "company_name": "Placeholder Capital",
            "title": "Quantitative Researcher",
            "locations": ["Chicago, IL"],
            "category": "Quant",
            "url": "https://example.com/fake-job-3",
            "date_posted": now,
        },
    ]


def send_email(subject, text, body_html):
    user = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
    to = os.environ.get("EMAIL_TO", user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.set_content(text)
    msg.add_alternative(body_html, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the digest instead of emailing")
    ap.add_argument("--feed-file", help="read the feed from a local file instead of the network")
    ap.add_argument("--test-email", action="store_true", help="email fake postings to verify delivery; leaves state untouched")
    args = ap.parse_args()

    now = time.time()
    if args.test_email:
        jobs = fake_jobs(now)
        text, body_html = render(jobs)
        send_email(f"[new grad] TEST — {len(jobs)} fake postings", text, body_html)
        print(f"sent test email with {len(jobs)} fake postings")
        return

    feed = json.loads(Path(args.feed_file).read_text()) if args.feed_file else fetch_feed()
    all_ids = {j["id"] for j in feed}
    relevant = {j["id"]: j for j in feed if is_relevant(j, now)}

    seen = load_seen()
    if seen is None:
        if not args.dry_run:
            save_seen(all_ids)
        print(f"bootstrapped: {len(all_ids)} ids recorded, {len(relevant)} currently relevant, no email sent")
        return

    new = [job for jid, job in relevant.items() if jid not in seen]
    if not args.dry_run:
        # Keep ids that are still upstream so a delisted-then-relisted job doesn't re-alert,
        # and drop ids that fell out of the feed entirely so state stays bounded.
        save_seen((seen & all_ids) | set(relevant))

    if not new:
        print("no new postings")
        return

    subject = f"[new grad] {len(new)} new posting{'s' if len(new) != 1 else ''}"
    text, body_html = render(new)
    if args.dry_run:
        print(subject)
        print(text)
        return
    send_email(subject, text, body_html)
    print(f"emailed {len(new)} postings")


if __name__ == "__main__":
    sys.exit(main())

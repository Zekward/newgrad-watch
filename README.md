# newgrad-watch

Emails you new-grad postings the moment they land in
[SimplifyJobs/New-Grad-Positions](https://github.com/SimplifyJobs/New-Grad-Positions).
Simplify scrapes company career pages hourly and commits new rows to
`.github/scripts/listings.json`; this repo polls that file three times a day,
diffs it against what it saw last time, and emails the delta.

## What gets emailed

A posting has to be `active`, `is_visible`, in one of `Software` / `AI/ML/Data` /
`Quant`, and posted within the last 7 days. Edit `CATEGORIES` and `MAX_AGE_DAYS`
at the top of [watch.py](watch.py) to change that.

`MAX_AGE_DAYS` matters more than it looks. Simplify frequently adds a listing to
the feed days or weeks after the company posted it, so "never seen before" and
"recently posted" are different things — without the cap, a first sighting of a
three-week-old job arrives looking like breaking news. Emails are ordered newest
first.

Each email carries at most `MAX_PER_EMAIL` (50) postings, newest first. Anything
over that stays unseen and rolls into the next run rather than being dropped, so
a backlog drains 50 at a time instead of arriving as one wall of text.

## Setup

Add three repo secrets (Settings → Secrets and variables → Actions):

| Secret | Value |
| --- | --- |
| `GMAIL_USER` | the Gmail address that sends |
| `GMAIL_APP_PASSWORD` | a 16-char app password from https://myaccount.google.com/apppasswords (needs 2FA on) |
| `EMAIL_TO` | where to deliver; defaults to `GMAIL_USER` if unset |

Then enable Actions. The workflow runs `0 13,17,21 * * *` — 9am / 1pm / 5pm US
Eastern — and on manual dispatch.

## State

`state/seen.json` is the set of listing ids already accounted for. The workflow
commits it back to the repo after each run that changes it. If the file is
missing, the run **bootstraps**: it records every id and sends no email, so you
never get one 900-item blast.

## Local use

```bash
python3 watch.py --dry-run          # print the digest instead of sending
python3 watch.py --feed-file f.json # use a local snapshot instead of the network
```

`--dry-run` never writes `state/seen.json`, so it won't swallow a delta that the
real run should have emailed.

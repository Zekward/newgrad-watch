# newgrad-watch

Aggregates new-grad software roles from the
[SimplifyJobs](https://github.com/SimplifyJobs/New-Grad-Positions) feed **and** 66 company job
boards, banks them in one store, and emails you a digest each morning.

## How it runs

Two jobs, deliberately separate:

| | When | What it does |
| --- | --- | --- |
| `collect.py` | every 4 hours | fetches every source, normalizes, appends new postings to `data/`. Sends nothing. |
| `notify.py` | 9am ET daily | emails everything banked since the last digest. Fetches nothing. |

Splitting them means a flaky job board can never cost you a digest, and a digest can be
re-sent without re-fetching. It also makes `data/` a queryable history rather than a
throwaway cache.

## The store

`data/jobs-YYYY-MM.ndjson`, one JSON record per line, append-only:

```json
{"id":"gh:spacex:864","url_key":"boards.greenhouse.io/spacex/jobs/864","source":"greenhouse",
 "company":"SpaceX","title":"New Graduate Engineer, Propulsion","locations":["Starbase, TX"],
 "category":"Software","url":"https://…","posted_at":1785622681,"first_seen_at":1785640000}
```

`posted_at` is what the source claims and is not trustworthy — Simplify backfills weeks-old
listings, and Workday reports only `"30+ Days Ago"`. **`first_seen_at` is when we saw it**,
which is what every "what's new" query uses. That's why there is no diffing and no seen-set:
the digest is just `first_seen_at > watermark`.

`url_key` (host + path, query stripped) dedupes the same job arriving from Simplify and from
the company's own board.

NDJSON rather than SQLite specifically because of git — text appends keep history small,
whereas a rewritten binary file would add megabytes per day.

## Sources

`companies.py` holds 66 verified boards across four platforms. Greenhouse, Ashby and Lever
need one slug; Workday needs `(tenant, wd number, site)`, none of which are guessable — read
them off the company's careers URL.

Add one by confirming the board responds, then adding a line:

```bash
curl -s "https://boards-api.greenhouse.io/v1/boards/SLUG/jobs" | python3 -c "import json,sys;print(len(json.load(sys.stdin)['jobs']),'jobs')"
```

A slug that goes stale returns zero rows silently, so `collect.py` prints a per-board
`ok/total` count every run.

Direct-board rows must name new-grad status in the title (`sources.NEW_GRAD_RE`) and must not
look senior or be an internship (`sources.EXCLUDE_RE`). Without that these boards are a
firehose — SpaceX alone lists 2,100 roles.

## Setup

Three repo secrets under Settings → Secrets and variables → Actions:

| Secret | Value |
| --- | --- |
| `GMAIL_USER` | the Gmail address that sends |
| `GMAIL_APP_PASSWORD` | 16-char app password from https://myaccount.google.com/apppasswords |
| `EMAIL_TO` | where to deliver; defaults to `GMAIL_USER` |

## Local use

```bash
python3 collect.py --dry-run     # what would be added, writes nothing
python3 notify.py  --dry-run     # print the digest, send nothing, move no watermark
python3 notify.py  --seed        # mark everything stored as sent (use after a bulk import)
```

`refresh-listings.sh` keeps a pruned local copy of the raw Simplify feed for poking at by
hand. Nothing in the pipeline reads it.

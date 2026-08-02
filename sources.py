"""Pull new-grad roles straight from company job boards.

Greenhouse, Ashby and Lever all expose public JSON with no auth. Each fetcher returns rows
in the same shape watch.py already uses for the Simplify feed, so the diff, digest and state
machinery work unchanged.

Unlike the Simplify feed these boards don't backfill — a posting shows up the day it opens —
so rows from here carry source="direct" and skip the age filter. First sighting is genuine.
"""

import json
import urllib.error
import urllib.request
from datetime import datetime

import companies

# A title has to say it's for new grads. Deliberately precision-first: these boards list every
# opening a company has, so anything looser buries the real ones (SpaceX alone posts 2,100 roles).
NEW_GRAD_TERMS = [
    "new grad", "new graduate", "university grad", "college grad", "entry level",
    "entry-level", "early career", "early in career", "campus", "rotational",
    "junior ", "associate engineer", "engineer i", "engineer 1", "apprentice",
]

# Rough bucketing so the digest can group these next to the Simplify rows.
CATEGORY_TERMS = [
    ("AI/ML/Data", ["machine learning", "ml ", "ai ", "data scien", "data eng", "research scien", "analytics"]),
    ("Quant", ["quant", "trading", "trader"]),
    ("Software", ["software", "engineer", "developer", "infrastructure", "backend", "frontend",
                  "full stack", "fullstack", "security", "platform", "systems"]),
]


def _get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "newgrad-watch"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _iso_to_epoch(s):
    if not s:
        return None
    try:
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def is_new_grad(title):
    return any(t in title.lower() for t in NEW_GRAD_TERMS)


def categorize(title):
    low = title.lower()
    for name, terms in CATEGORY_TERMS:
        if any(t in low for t in terms):
            return name
    return "Software"


def _row(company, title, locations, url, job_id, posted):
    return {
        "id": f"direct:{job_id}",
        "source": "direct",
        "company_name": company,
        "title": title,
        "locations": [l for l in locations if l],
        "url": url,
        "category": categorize(title),
        "date_posted": posted,
        "active": True,
        "is_visible": True,
    }


def greenhouse(company, slug, now):
    out = []
    for j in _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs").get("jobs", []):
        if not is_new_grad(j.get("title", "")):
            continue
        out.append(_row(company, j["title"], [j.get("location", {}).get("name", "")],
                        f"https://boards.greenhouse.io/{slug}/jobs/{j['id']}",
                        f"gh:{slug}:{j['id']}", _iso_to_epoch(j.get("updated_at")) or now))
    return out


def ashby(company, slug, now):
    out = []
    for j in _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").get("jobs", []):
        if not is_new_grad(j.get("title", "")):
            continue
        out.append(_row(company, j["title"], [j.get("location", "")],
                        j.get("jobUrl") or f"https://jobs.ashbyhq.com/{slug}",
                        f"ashby:{slug}:{j.get('id')}", _iso_to_epoch(j.get("publishedAt")) or now))
    return out


def lever(company, slug, now):
    out = []
    for j in _get(f"https://api.lever.co/v0/postings/{slug}?mode=json"):
        if not is_new_grad(j.get("text", "")):
            continue
        posted = j.get("createdAt")
        out.append(_row(company, j["text"], [(j.get("categories") or {}).get("location", "")],
                        j.get("hostedUrl", ""), f"lever:{slug}:{j.get('id')}",
                        int(posted / 1000) if posted else now))
    return out


FETCHERS = {"greenhouse": greenhouse, "ashby": ashby, "lever": lever}


def fetch_all(now):
    """Every new-grad row across the roster. A board that errors is skipped with a warning
    rather than failing the run — one dead slug shouldn't cost you the other thirteen."""
    rows, empty = [], []
    for platform, entries in companies.ROSTER.items():
        for company, slug in entries:
            try:
                found = FETCHERS[platform](company, slug, now)
            except (urllib.error.URLError, json.JSONDecodeError, KeyError, TimeoutError) as e:
                print(f"  warn: {company} ({platform}/{slug}) failed: {e}")
                empty.append(company)
                continue
            rows.extend(found)
    if empty:
        print(f"  warn: {len(empty)} board(s) unreachable: {', '.join(empty)}")
    return rows

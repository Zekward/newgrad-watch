"""Pull new-grad roles straight from company job boards.

Greenhouse, Ashby and Lever all expose public JSON with no auth. Each fetcher returns rows
in the same shape watch.py already uses for the Simplify feed, so the diff, digest and state
machinery work unchanged.

Unlike the Simplify feed these boards don't backfill — a posting shows up the day it opens —
so rows from here carry source="direct" and skip the age filter. First sighting is genuine.
"""

import json
import re
import urllib.error
from concurrent import futures
import urllib.request
from datetime import datetime

import companies

# A title has to say it's for new grads. Deliberately precision-first: these boards list every
# opening a company has, so anything looser buries the real ones (SpaceX alone posts 2,100 roles).
# Word-bounded so "Engineer 1st Shift" doesn't read as "Engineer 1".
NEW_GRAD_RE = re.compile(
    r"new grad|new graduate|university grad|college grad|entry.level|early career"
    r"|early in career|\bcampus\b|rotational program|graduate program"
    r"|\bjunior\b|associate engineer|\bengineer\s+(?:i|1)\b|\bapprentice\b",
    re.I,
)

# Outranks any new-grad phrasing. Seniority words catch the people who *run* grad programs
# rather than the roles in them ("Director, Campus Recruitment Lead"); \bintern\b drops
# internships, which are a different search. "Internal" is safe — the boundary won't match.
EXCLUDE_RE = re.compile(
    r"\b(?:senior|sr\.?|staff|principal|director|manager|head of|vp|vice president|lead)\b"
    r"|recruit|\bintern\b|\binternship\b", re.I,
)

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
    return bool(NEW_GRAD_RE.search(title)) and not EXCLUDE_RE.search(title)


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


# Workday caps pages at 20 rows and some tenants hold thousands of roles, so we never list a
# board wholesale — we run a handful of targeted searches and union the hits. Four queries beats
# 100 paged requests for a tenant like NVIDIA.
WORKDAY_QUERIES = ["new college graduate", "new grad", "university graduate", "early career"]
WORKDAY_MAX_PER_QUERY = 60


def _post(url, payload, timeout=25):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json",
                 "User-Agent": "newgrad-watch"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _workday_posted(text, now):
    """Workday reports age as English, not a date: 'Posted Today', 'Posted 5 Days Ago',
    'Posted 30+ Days Ago'. The '30+' case is a floor, so treat it as exactly 30."""
    t = (text or "").lower()
    if "today" in t:
        days = 0
    elif "yesterday" in t:
        days = 1
    else:
        m = re.search(r"(\d+)", t)
        days = int(m.group(1)) if m else 30
    return int(now - days * 86400)


def workday(company, spec, now):
    tenant, wd, site = spec
    base = f"https://{tenant}.wd{wd}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}/jobs"
    out, seen = [], set()
    for query in WORKDAY_QUERIES:
        offset = 0
        while offset < WORKDAY_MAX_PER_QUERY:
            page = _post(api, {"appliedFacets": {}, "limit": 20, "offset": offset,
                               "searchText": query})
            postings = page.get("jobPostings", [])
            for j in postings:
                title = j.get("title", "")
                req_id = (j.get("bulletFields") or [None])[0] or j.get("externalPath")
                if req_id in seen or not is_new_grad(title):
                    continue
                seen.add(req_id)
                out.append(_row(company, title, [j.get("locationsText", "")],
                                f"{base}/en-US/{site}{j.get('externalPath', '')}",
                                f"wd:{tenant}:{req_id}",
                                _workday_posted(j.get("postedOn"), now)))
            offset += 20
            if len(postings) < 20 or offset >= page.get("total", 0):
                break
    return out


FETCHERS = {"greenhouse": greenhouse, "ashby": ashby, "lever": lever, "workday": workday}


def fetch_all(now, workers=12):
    """Every new-grad row across the roster, fetched concurrently. A board that errors is
    skipped with a warning rather than failing the run — one dead slug shouldn't cost you
    the other fifty-seven."""
    targets = [(p, c, s) for p, entries in companies.ROSTER.items() for c, s in entries]

    def one(target):
        platform, company, slug = target
        try:
            return company, FETCHERS[platform](company, slug, now), None
        except Exception as e:  # network, JSON, or a slug that stopped resolving
            return company, [], f"{platform}/{slug}: {e}"

    rows, failed = [], []
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for company, found, err in pool.map(one, targets):
            if err:
                failed.append(f"{company} ({err})")
            rows.extend(found)
    print(f"  boards: {len(targets) - len(failed)}/{len(targets)} ok, {len(rows)} new-grad rows")
    for f in failed:
        print(f"  warn: {f}")
    return rows

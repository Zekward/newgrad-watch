#!/bin/bash
# Refresh the local snapshot of the upstream feed. Downloads to a temp file and moves it
# into place so a reader never sees a half-written 12MB file.
set -euo pipefail

DEST="$(cd "$(dirname "$0")" && pwd)/listings.json"
TMP="$(mktemp "${TMPDIR:-/tmp}/listings.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

curl -sSLf --max-time 120 \
  -o "$TMP" \
  https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json

# Validate, then drop anything posted more than KEEP_DAYS ago. The upstream file is mostly
# an archive of closed listings; keeping only the recent window cuts it from 12MB to ~3MB.
# Refuses to install a truncated or malformed download over a good snapshot.
KEEP_DAYS=60
python3 - "$TMP" "$KEEP_DAYS" <<'PY'
import json, sys, time
path, keep_days = sys.argv[1], int(sys.argv[2])
rows = json.load(open(path))
if len(rows) < 1000:
    sys.exit(f"refusing to install a {len(rows)}-row download")
cutoff = time.time() - keep_days * 86400
kept = [r for r in rows if r.get("date_posted", 0) >= cutoff]
json.dump(kept, open(path, "w"), indent=1)
print(f"kept {len(kept)} of {len(rows)} rows (last {keep_days}d)")
PY

mv "$TMP" "$DEST"
trap - EXIT
echo "$(date '+%Y-%m-%d %H:%M:%S') refreshed -> $(python3 -c "import json;print(len(json.load(open('$DEST'))))") rows, $(du -h "$DEST" | cut -f1)"

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

# Refuse to install a truncated or malformed download over a good snapshot.
python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if len(d) > 1000 else 1)" "$TMP"

mv "$TMP" "$DEST"
trap - EXIT
echo "$(date '+%Y-%m-%d %H:%M:%S') refreshed $(python3 -c "import json;print(len(json.load(open('$DEST'))))") rows"

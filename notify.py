#!/usr/bin/env python3
"""Email everything the collector has banked since the last digest. Fetches nothing.

Selection is `first_seen_at > watermark` — no diffing, and immune to the unreliable
posted-at dates upstream sources report.
"""

import argparse
import sys
import time

import digest
import store

MAX_PER_EMAIL = 100


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print the digest, send nothing, move no watermark")
    ap.add_argument("--since", type=int, help="override the watermark (epoch seconds)")
    ap.add_argument("--seed", action="store_true",
                    help="mark everything currently stored as already sent, without emailing")
    ap.add_argument("--recent", type=int, metavar="N",
                    help="email the N most recently posted jobs in the store and leave the "
                         "watermark alone, so the next scheduled digest is unaffected")
    args = ap.parse_args()

    now = time.time()

    if args.recent:
        picks = sorted(store.read_all(), key=lambda r: r.get("posted_at", 0),
                       reverse=True)[:args.recent]
        if not picks:
            print("store is empty")
            return 0
        text, body_html = digest.render(picks, now)
        subject = f"[new grad] {len(picks)} most recent postings (snapshot)"
        if args.dry_run:
            print(subject)
            print(text)
            return 0
        digest.send_email(subject, text, body_html)
        print(f"emailed {len(picks)} most recent postings; watermark unchanged")
        return 0

    if args.seed:
        store.set_watermark(now)
        print(f"watermark set to {int(now)}; nothing already stored will be emailed")
        return 0

    mark = args.since if args.since is not None else store.get_watermark()
    pending = store.read_since(mark)
    if not pending:
        print("no new postings")
        return 0

    # Oldest sighting first, so a backlog drains in order instead of stranding the tail.
    batch = pending[:MAX_PER_EMAIL]
    held = len(pending) - len(batch)

    subject = f"[new grad] {len(batch)} new posting{'s' if len(batch) != 1 else ''}"
    if held:
        subject += f" (+{held} queued)"
    text, body_html = digest.render(batch, now, held)

    if args.dry_run:
        print(subject)
        print(text)
        return 0

    digest.send_email(subject, text, body_html)
    # Advance only as far as what actually went out, so the held-back tail is not skipped.
    store.set_watermark(max(r["first_seen_at"] for r in batch))
    print(f"emailed {len(batch)} postings" + (f", {held} held for tomorrow" if held else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

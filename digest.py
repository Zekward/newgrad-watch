"""Rendering and delivery for the daily digest."""

import html
import os
import re
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage

try:
    from zoneinfo import ZoneInfo

    EASTERN = ZoneInfo("America/New_York")
except Exception:  # no system tzdata available
    EASTERN = timezone.utc


# Where a posting came from. Greenhouse/Ashby/Lever/Workday mean we read the company's own
# board directly; Simplify means it came via the aggregated feed, which lags and can carry
# a miscategorized row.
SOURCE_LABELS = {
    "simplify": "Simplify feed",
    "greenhouse": "Greenhouse (direct)",
    "ashby": "Ashby (direct)",
    "lever": "Lever (direct)",
    "workday": "Workday (direct)",
}


def source_label(source):
    return SOURCE_LABELS.get(source, source or "unknown")


def posted_str(ts, now):
    """'Jul 31 6:14pm ET · 5h ago'. Sources that report only a date land on UTC midnight,
    so those get the date alone rather than a fabricated 8:00pm."""
    dt = datetime.fromtimestamp(ts, EASTERN)
    stamp = dt.strftime("%b %d")
    if ts % 86400:
        stamp += dt.strftime(" %-I:%M%p").lower() + " ET"
    age = now - ts
    if age < 3600:
        rel = f"{int(age // 60)}m ago"
    elif age < 48 * 3600:
        rel = f"{int(age // 3600)}h ago"
    else:
        rel = f"{int(age // 86400)}d ago"
    return f"{stamp} · {rel}"


def render(records, now, held=0):
    """Return (plain_text, html). Newest posting first."""
    records = sorted(records, key=lambda r: r.get("posted_at", 0), reverse=True)
    lines, rows = [], []
    for r in records:
        where = ", ".join(r.get("locations") or []) or "—"
        posted = posted_str(r.get("posted_at", now), now)
        src = source_label(r.get("source"))
        direct = r.get("source") != "simplify"
        lines.append(f"{r['company']} — {r['title']}\n  {where} · {r['category']} · posted {posted}"
                     f"\n  source: {src}\n  {r['url']}\n")
        pill_bg, pill_fg = ("#e8f3ec", "#1c6b3f") if direct else ("#eef1f6", "#4a5566")
        rows.append(
            "<tr>"
            f"<td style='padding:8px 12px 8px 0;vertical-align:top'><b>{html.escape(r['company'] or '')}</b></td>"
            f"<td style='padding:8px 0'><a href='{html.escape(r['url'] or '')}'>{html.escape(r['title'] or '')}</a>"
            f"<div style='color:#666;font-size:13px'>{html.escape(where)} · {html.escape(r['category'] or '')}"
            f" · posted {posted}</div>"
            f"<div style='margin-top:4px'><span style='font-size:11px;letter-spacing:.04em;"
            f"background:{pill_bg};color:{pill_fg};border-radius:4px;padding:2px 7px'>"
            f"{html.escape(src)}</span></div></td>"
            "</tr>"
        )
    overflow = f" {held} more are queued for tomorrow." if held else ""
    if held:
        lines.append(f"({held} more queued for tomorrow.)")
    body_html = (
        "<div style='font-family:-apple-system,Segoe UI,sans-serif;font-size:14px'>"
        f"<p>{len(records)} new posting{'s' if len(records) != 1 else ''}.{overflow}</p>"
        f"<table style='border-collapse:collapse'>{''.join(rows)}</table>"
        "<p style='color:#888;font-size:12px'>Simplify feed + company job boards</p></div>"
    )
    return "\n".join(lines), body_html


def send_email(subject, text, body_html):
    user = os.environ["GMAIL_USER"]
    # Google renders app passwords in four groups separated by non-breaking spaces,
    # so strip all whitespace rather than just U+0020.
    password = "".join(os.environ["GMAIL_APP_PASSWORD"].split())
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

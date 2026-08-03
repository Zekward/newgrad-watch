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
        via = "" if r.get("source") == "simplify" else f" · via {r['company']} careers"
        lines.append(f"{r['company']} — {r['title']}\n  {where} · {r['category']} · posted {posted}\n  {r['url']}\n")
        rows.append(
            "<tr>"
            f"<td style='padding:8px 12px 8px 0;vertical-align:top'><b>{html.escape(r['company'] or '')}</b></td>"
            f"<td style='padding:8px 0'><a href='{html.escape(r['url'] or '')}'>{html.escape(r['title'] or '')}</a>"
            f"<div style='color:#666;font-size:13px'>{html.escape(where)} · {html.escape(r['category'] or '')}"
            f" · posted {posted}{html.escape(via)}</div></td>"
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

# Oil & Gas Job Agent — Email + Telegram messenger
import smtplib, logging, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

from config import EMAIL_PROVIDER, RESEND_API_KEY, FROM_EMAIL, FROM_NAME, RECIPIENT, TG_TOKEN, TG_CHAT


# ═══════════════════════════════════════════════════════════════
#  EMAIL via Resend API
# ═══════════════════════════════════════════════════════════════

def send_email(html, subject_date):
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY not set")
        return False
    subj = f"🛢️ Oil & Gas Visa-Sponsored Jobs — {subject_date}"
    try:
        r = requests.post("https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={"from": f"{FROM_NAME} <{FROM_EMAIL}>", "to": [RECIPIENT],
                  "subject": subj, "html": html}, timeout=15)
        ok = r.status_code == 200
        if ok: logger.info("✅ Email sent to %s", RECIPIENT)
        else: logger.error("❌ Resend: %s %s", r.status_code, r.text)
        return ok
    except Exception as e:
        logger.error("❌ Resend error: %s", e)
        return False


def compose_email(jobs, date_str=None):
    if not date_str: date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    total = len(jobs)
    by_country = {}
    for j in jobs:
        by_country.setdefault(j.get("country","Unknown"), []).append(j)

    rows = ""
    for country, cjobs in sorted(by_country.items()):
        for j in cjobs:
            t = esc(j.get("title","N/A")); co = esc(j.get("company","Unknown"))
            u = esc(j.get("url","#")); src = esc(j.get("source","Web"))
            rows += f"""
            <tr>
                <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;"><strong style="color:#1a5276;">{t}</strong><br><span style="color:#555;font-size:13px;">🏢 {co}</span></td>
                <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;">🌍 {esc(country)}</td>
                <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;"><span style="font-size:12px;color:#888;">{src}</span></td>
                <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;text-align:center;"><a href="{u}" target="_blank" style="background:#1a5276;color:#fff;padding:6px 14px;border-radius:4px;text-decoration:none;font-size:13px;font-weight:bold;">Apply →</a></td>
            </tr>"""

    empty = "" if rows.strip() else '<p style="text-align:center;color:#888;padding:30px 0;">No new visa-sponsored oil & gas jobs found. Will search again next Tuesday/Friday.</p>'

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:20px 0;"><tr><td align="center">
<table width="700" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
<tr><td style="background:linear-gradient(135deg,#0d3b66,#1a5276);padding:28px 32px;text-align:center;">
<h1 style="color:#fff;margin:0;font-size:22px;">🛢️ Oil & Gas Job Vacancies</h1>
<p style="color:#bdd3e8;margin:6px 0 0;font-size:14px;">Visa-Sponsored Positions — {date_str}</p></td></tr>
<tr><td style="padding:20px 32px;background:#eaf2f8;">
<p style="margin:0;font-size:15px;color:#1a3a4f;"><strong>{total}</strong> new vacancy(s) across <strong>{len(by_country)}</strong> country(s). All listings below include <strong>visa sponsorship for foreigners</strong>.</p></td></tr>
<tr><td style="padding:16px 24px;">
<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
<thead><tr style="background:#0d3b66;color:#fff;">
<th style="padding:10px 12px;text-align:left;font-size:13px;">Position / Company</th>
<th style="padding:10px 12px;text-align:left;font-size:13px;">Country</th>
<th style="padding:10px 12px;text-align:left;font-size:13px;">Source</th>
<th style="padding:10px 12px;text-align:center;font-size:13px;">Apply</th></tr></thead>
<tbody>{rows}</tbody></table>{empty}</td></tr>
<tr><td style="padding:20px 32px;background:#fafafa;border-top:1px solid #e0e0e0;text-align:center;">
<p style="margin:0;font-size:12px;color:#999;">Oil & Gas Job Agent • Tue & Fri • 50 countries • 14 positions • Visa sponsorship required</p></td></tr>
</table></td></tr></table></body></html>"""


# ═══════════════════════════════════════════════════════════════
#  TELEGRAM
# ═══════════════════════════════════════════════════════════════

def send_telegram(jobs, dry_run=False):
    if not TG_TOKEN or not TG_CHAT:
        logger.info("Telegram not configured — skipping")
        return True
    html = compose_tg(jobs)
    if dry_run:
        logger.info("TG DRY RUN:\n%s", html[:400])
        return True
    try:
        for msg in _split(html, 4000):
            r = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=15)
            if not r.json().get("ok"):
                logger.error("TG error: %s", r.json())
                return False
        logger.info("✅ Telegram sent")
        return True
    except Exception as e:
        logger.error("TG error: %s", e)
        return False


def compose_tg(jobs, date_str=None):
    if not date_str: date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    if not jobs:
        return f"🛢️ <b>Oil & Gas Job Agent</b> — {date_str}\n\n❌ No new visa-sponsored jobs found."
    total = len(jobs)
    by_country = {}
    for j in jobs: by_country.setdefault(j.get("country","Unknown"), []).append(j)
    lines = [
        f"🛢️ <b>Oil & Gas Job Vacancies — {date_str}</b>",
        "", f"📊 <b>{total}</b> new vacancy(s) across <b>{len(by_country)}</b> countries",
        "✅ All include visa sponsorship", "",
    ]
    for country, cjobs in sorted(by_country.items()):
        lines.append(f"🌍 <b>{esc(country)}</b> ({len(cjobs)})")
        for j in cjobs[:3]:
            t = esc(j.get("title","N/A")); co = esc(j.get("company","Unknown"))
            u = esc(j.get("url",""))
            line = f"  • <b>{t}</b> — {co}"
            if u: line += f"\n    <a href='{u}'>Apply →</a>"
            lines.append(line)
        if len(cjobs) > 3: lines.append(f"  …{len(cjobs)-3} more (see email)")
        lines.append("")
    lines.append(f"📬 Full listing emailed to {RECIPIENT}")
    return "\n".join(lines)


def esc(text):
    return str(text).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def _split(text, n=4000):
    if len(text) <= n: return [text]
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur)+len(line)+1 > n: parts.append(cur); cur = line
        else: cur += ("\n"+line) if cur else line
    if cur: parts.append(cur)
    return parts

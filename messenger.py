#!/usr/bin/env python3
# =============================================================================
# Oil & Gas Job Agent — Multi-Provider Email + Telegram Messenger
# Supports: Brevo, SendGrid, Resend, Mailgun, Gmail, Custom SMTP
# =============================================================================

import smtplib, logging, os, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)

# ---- Local config references (set at import time by caller) ----
EMAIL_PROVIDER   = os.getenv("EMAIL_PROVIDER", "brevo")
FROM_EMAIL       = os.getenv("FROM_EMAIL", "jobs@oil-gas-agent.com")
FROM_NAME        = os.getenv("FROM_NAME", "Oil & Gas Job Agent")
RECIPIENT_EMAIL  = os.getenv("RECIPIENT_EMAIL", "gregslum@gmail.com")

BREVO_SMTP_KEY   = os.getenv("BREVO_SMTP_KEY", "")
BREVO_LOGIN      = os.getenv("BREVO_LOGIN", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
RESEND_API_KEY   = os.getenv("RESEND_API_KEY", "")
MAILGUN_API_KEY  = os.getenv("MAILGUN_API_KEY", "")
MAILGUN_DOMAIN   = os.getenv("MAILGUN_DOMAIN", "")
GMAIL_ADDRESS    = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASS   = os.getenv("GMAIL_APP_PASS", "")
CUSTOM_SMTP_HOST = os.getenv("CUSTOM_SMTP_HOST", "")
CUSTOM_SMTP_PORT = int(os.getenv("CUSTOM_SMTP_PORT", "587"))
CUSTOM_SMTP_USER = os.getenv("CUSTOM_SMTP_USER", "")
CUSTOM_SMTP_PASS = os.getenv("CUSTOM_SMTP_PASS", "")


def send_email(html_body: str, subject_date: str) -> bool:
    """Route to the correct email provider. Returns True on success."""
    providers = {
        "brevo":    _send_brevo,
        "sendgrid": _send_sendgrid,
        "resend":   _send_resend,
        "mailgun":  _send_mailgun,
        "gmail":    _send_gmail,
        "custom":   _send_custom,
    }
    func = providers.get(EMAIL_PROVIDER)
    if not func:
        logger.error("Unknown EMAIL_PROVIDER: %s", EMAIL_PROVIDER)
        return False
    logger.info("Sending email via %s to %s", EMAIL_PROVIDER, RECIPIENT_EMAIL)
    return func(html_body, subject_date)


# ---------------------------------------------------------------------------
# BREVO (Sendinblue) — RECOMMENDED — 300 emails/day free
# ---------------------------------------------------------------------------

def _send_brevo(html_body: str, subject_date: str) -> bool:
    if not BREVO_SMTP_KEY:
        logger.error("BREVO_SMTP_KEY not set!")
        return False
    subject = f"🛢️ Oil & Gas Visa-Sponsored Jobs — {subject_date}"
    msg = _build_mime(html_body, subject)
    try:
        with smtplib.SMTP("smtp-relay.brevo.com", 587, timeout=30) as srv:
            srv.ehlo(); srv.starttls(); srv.ehlo()
            srv.login(BREVO_LOGIN or FROM_EMAIL, BREVO_SMTP_KEY)
            srv.sendmail(FROM_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        logger.info("✅ Brevo: email sent to %s", RECIPIENT_EMAIL)
        return True
    except Exception as e:
        logger.error("❌ Brevo failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# SENDGRID — 100 emails/day free
# ---------------------------------------------------------------------------

def _send_sendgrid(html_body: str, subject_date: str) -> bool:
    if not SENDGRID_API_KEY:
        logger.error("SENDGRID_API_KEY not set!")
        return False
    subject = f"🛢️ Oil & Gas Visa-Sponsored Jobs — {subject_date}"
    msg = _build_mime(html_body, subject)
    try:
        with smtplib.SMTP("smtp.sendgrid.net", 587, timeout=30) as srv:
            srv.ehlo(); srv.starttls(); srv.ehlo()
            srv.login("apikey", SENDGRID_API_KEY)
            srv.sendmail(FROM_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        logger.info("✅ SendGrid: email sent to %s", RECIPIENT_EMAIL)
        return True
    except Exception as e:
        logger.error("❌ SendGrid failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# RESEND — 100 emails/day free — REST API (no SMTP needed!)
# ---------------------------------------------------------------------------

def _send_resend(html_body: str, subject_date: str) -> bool:
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY not set!")
        return False
    subject = f"🛢️ Oil & Gas Visa-Sponsored Jobs — {subject_date}"
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [RECIPIENT_EMAIL],
                "subject": subject,
                "html": html_body,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            logger.info("✅ Resend: email sent to %s (id: %s)", RECIPIENT_EMAIL, resp.json().get("id", "?"))
            return True
        else:
            logger.error("❌ Resend failed: %s %s", resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.error("❌ Resend error: %s", e)
        return False


# ---------------------------------------------------------------------------
# MAILGUN — REST API
# ---------------------------------------------------------------------------

def _send_mailgun(html_body: str, subject_date: str) -> bool:
    if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
        logger.error("MAILGUN_API_KEY and MAILGUN_DOMAIN must be set!")
        return False
    subject = f"🛢️ Oil & Gas Visa-Sponsored Jobs — {subject_date}"
    try:
        resp = requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
            auth=("api", MAILGUN_API_KEY),
            data={
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": [RECIPIENT_EMAIL],
                "subject": subject,
                "html": html_body,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            logger.info("✅ Mailgun: email sent to %s", RECIPIENT_EMAIL)
            return True
        else:
            logger.error("❌ Mailgun failed: %s %s", resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.error("❌ Mailgun error: %s", e)
        return False


# ---------------------------------------------------------------------------
# GMAIL — needs App Password
# ---------------------------------------------------------------------------

def _send_gmail(html_body: str, subject_date: str) -> bool:
    if not GMAIL_ADDRESS or not GMAIL_APP_PASS:
        logger.error("GMAIL_ADDRESS and GMAIL_APP_PASS must be set!")
        return False
    subject = f"🛢️ Oil & Gas Visa-Sponsored Jobs — {subject_date}"
    msg = _build_mime(html_body, subject, from_addr=GMAIL_ADDRESS)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as srv:
            srv.ehlo(); srv.starttls(); srv.ehlo()
            srv.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
            srv.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())
        logger.info("✅ Gmail: email sent to %s", RECIPIENT_EMAIL)
        return True
    except Exception as e:
        logger.error("❌ Gmail failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# CUSTOM SMTP
# ---------------------------------------------------------------------------

def _send_custom(html_body: str, subject_date: str) -> bool:
    if not CUSTOM_SMTP_HOST:
        logger.error("CUSTOM_SMTP_HOST not set!")
        return False
    subject = f"🛢️ Oil & Gas Visa-Sponsored Jobs — {subject_date}"
    from_addr = CUSTOM_SMTP_USER or FROM_EMAIL
    msg = _build_mime(html_body, subject, from_addr=from_addr)
    try:
        with smtplib.SMTP(CUSTOM_SMTP_HOST, CUSTOM_SMTP_PORT, timeout=30) as srv:
            srv.ehlo(); srv.starttls(); srv.ehlo()
            if CUSTOM_SMTP_USER:
                srv.login(CUSTOM_SMTP_USER, CUSTOM_SMTP_PASS)
            srv.sendmail(from_addr, RECIPIENT_EMAIL, msg.as_string())
        logger.info("✅ Custom SMTP: email sent to %s", RECIPIENT_EMAIL)
        return True
    except Exception as e:
        logger.error("❌ Custom SMTP failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_mime(html_body: str, subject: str, from_addr: str = None) -> MIMEMultipart:
    """Build a MIME email message."""
    addr = from_addr or FROM_EMAIL
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((FROM_NAME, addr))
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


# ===========================================================================
# HTML Email Composer
# ===========================================================================

def compose_html_email(jobs: list, search_date: str = None) -> str:
    """Build a professional HTML email listing all found jobs."""
    if not search_date:
        search_date = datetime.now(timezone.utc).strftime("%B %d, %Y")

    total = len(jobs)
    by_country = {}
    for j in jobs:
        by_country.setdefault(j.get("country", "Unknown"), []).append(j)

    rows = ""
    for country, cjobs in sorted(by_country.items()):
        for job in cjobs:
            title = esc(job.get("title", "N/A"))
            company = esc(job.get("company", "Unknown"))
            url = esc(job.get("url", "#"))
            source = esc(job.get("source", "Web"))
            rows += """
            <tr>
                <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;vertical-align:top;">
                    <strong style="color:#1a5276;">""" + title + """</strong><br>
                    <span style="color:#555;font-size:13px;">🏢 """ + company + """</span>
                </td>
                <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;vertical-align:top;">🌍 """ + esc(country) + """</td>
                <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;vertical-align:top;"><span style="font-size:12px;color:#888;">""" + source + """</span></td>
                <td style="padding:10px 12px;border-bottom:1px solid #e0e0e0;vertical-align:top;text-align:center;">
                    <a href=""" + '"' + url + '"' + """ target="_blank" style="display:inline-block;background:#1a5276;color:#fff;padding:6px 14px;border-radius:4px;text-decoration:none;font-size:13px;font-weight:bold;">Apply →</a>
                </td>
            </tr>"""

    empty_note = ""
    if not rows.strip():
        empty_note = '<p style="text-align:center;color:#888;padding:30px 0;margin:0;">No new visa-sponsored oil & gas jobs found this cycle. The agent will search again next Tuesday or Friday.</p>'

    provider_line = os.getenv("EMAIL_PROVIDER", "brevo")

    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:20px 0;"><tr><td align="center">
<table width="700" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
<tr><td style="background:linear-gradient(135deg,#0d3b66,#1a5276);padding:28px 32px;text-align:center;">
<h1 style="color:#fff;margin:0;font-size:22px;">🛢️ Oil & Gas Job Vacancies</h1>
<p style="color:#bdd3e8;margin:6px 0 0;font-size:14px;">Visa-Sponsored Positions — """ + search_date + """</p></td></tr>
<tr><td style="padding:20px 32px;background:#eaf2f8;">
<p style="margin:0;font-size:15px;color:#1a3a4f;"><strong>""" + str(total) + """</strong> new vacancy(s) across <strong>""" + str(len(by_country)) + """</strong> country(s). All listings below include <strong>visa sponsorship for foreigners</strong>.</p></td></tr>
<tr><td style="padding:16px 24px;">
<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
<thead><tr style="background:#0d3b66;color:#fff;">
<th style="padding:10px 12px;text-align:left;font-size:13px;">Position / Company</th>
<th style="padding:10px 12px;text-align:left;font-size:13px;">Country</th>
<th style="padding:10px 12px;text-align:left;font-size:13px;">Source</th>
<th style="padding:10px 12px;text-align:center;font-size:13px;">Apply</th></tr></thead>
<tbody>""" + rows + """</tbody></table>""" + empty_note + """</td></tr>
<tr><td style="padding:20px 32px;background:#fafafa;border-top:1px solid #e0e0e0;text-align:center;">
<p style="margin:0;font-size:12px;color:#999;">Automatically generated by Oil & Gas Job Agent via """ + provider_line + """<br>Next email: next Tuesday or Friday | 50 countries | 14 positions | Visa sponsorship required</p></td></tr>
</table></td></tr></table></body></html>"""


# ===========================================================================
# Telegram Composer
# ===========================================================================

def compose_telegram_html(jobs: list, search_date: str = None) -> str:
    """Build a Telegram HTML message summary."""
    if not search_date:
        search_date = datetime.now(timezone.utc).strftime("%B %d, %Y")

    if not jobs:
        return "🛢️ <b>Oil & Gas Job Agent</b> — " + search_date + "\n\n❌ No new visa-sponsored jobs found."

    total = len(jobs)
    by_country = {}
    for j in jobs:
        by_country.setdefault(j.get("country", "Unknown"), []).append(j)

    lines = [
        "🛢️ <b>Oil & Gas Job Vacancies — " + search_date + "</b>",
        "",
        "📊 <b>" + str(total) + "</b> new vacancy(s) across <b>" + str(len(by_country)) + "</b> countries",
        "✅ All include visa sponsorship",
        "",
    ]

    for country, cjobs in sorted(by_country.items()):
        lines.append("🌍 <b>" + esc(country) + "</b> (" + str(len(cjobs)) + ")")
        for j in cjobs[:3]:
            title = esc(j.get("title", "N/A"))
            company = esc(j.get("company", "Unknown"))
            url = esc(j.get("url", ""))
            line = "  • <b>" + title + "</b> — " + company
            if url:
                line += "\n    <a href='" + url + "'>Apply →</a>"
            lines.append(line)
        if len(cjobs) > 3:
            lines.append("  …and " + str(len(cjobs) - 3) + " more (see email)")
        lines.append("")

    lines.append("📬 Full listing emailed to " + RECIPIENT_EMAIL)
    return "\n".join(lines)


def compose_telegram_text(jobs: list, search_date: str = None) -> str:
    """Build a Telegram Markdown text summary."""
    if not search_date:
        search_date = datetime.now(timezone.utc).strftime("%B %d, %Y")

    if not jobs:
        return "🛢️ *Oil & Gas Job Agent* — " + search_date + "\n\n❌ No new visa-sponsored jobs found."

    total = len(jobs)
    by_country = {}
    for j in jobs:
        by_country.setdefault(j.get("country", "Unknown"), []).append(j)

    lines = [
        "🛢️ *Oil & Gas Job Vacancies — " + search_date + "*",
        "",
        "📊 *" + str(total) + "* new vacancy(s) across *" + str(len(by_country)) + "* countries",
        "✅ All include visa sponsorship",
        "",
    ]

    for country, cjobs in sorted(by_country.items()):
        lines.append("🌍 *" + country + "* (" + str(len(cjobs)) + ")")
        for j in cjobs[:3]:
            title = j.get("title", "N/A")
            company = j.get("company", "Unknown")
            url = j.get("url", "")
            line = "  • *" + title + "* — " + company
            if url:
                line += "\n    [Apply →](" + url + ")"
            lines.append(line)
        if len(cjobs) > 3:
            lines.append("  …and " + str(len(cjobs) - 3) + " more (see email)")
        lines.append("")

    lines.append("📬 Full listing sent to " + RECIPIENT_EMAIL)
    return "\n".join(lines)


def esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

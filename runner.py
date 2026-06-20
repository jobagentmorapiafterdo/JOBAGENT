#!/usr/bin/env python3
# Oil & Gas Job Agent — Core Runner (Tue/Fri split)
import os, sys, json, logging, argparse
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("runner")

import requests
from job_searcher import JobSearcher
from database import JobDatabase
from messenger import send_email, compose_html_email, compose_telegram_html


def get_todays_positions():
    from config import POSITIONS_WEEK
    wd = datetime.now().isoweekday()
    if wd == 2: return POSITIONS_WEEK["tuesday"], "tuesday"
    if wd == 5: return POSITIONS_WEEK["friday"], "friday"
    from config import POSITIONS
    return POSITIONS, "all"


def run_pipeline(send_email_flag=True, send_telegram_flag=True, dry_run=False):
    email_provider = os.getenv("EMAIL_PROVIDER", "resend")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    recipient = os.getenv("RECIPIENT_EMAIL", "gregslum@gmail.com")
    serper_key = os.getenv("SERPER_API_KEY", "")

    positions, day_label = get_todays_positions()
    from config import COUNTRIES
    total_q = len(positions) * len(COUNTRIES)

    logger.info("=" * 60)
    logger.info("🛢️  Oil & Gas Job Agent — Pipeline Start")
    logger.info("    Day: %s (%d positions)", day_label, len(positions))
    logger.info("    Queries: %d (%d positions × %d countries)", total_q, len(positions), len(COUNTRIES))
    logger.info("    Email: %s → %s", email_provider, recipient)
    logger.info("    Telegram: %s", "✅" if (telegram_token and telegram_chat_id) else "❌")
    logger.info("=" * 60)

    db = JobDatabase("jobs.db")
    searcher = JobSearcher()

    def progress(n, total, pos, country):
        if n % 10 == 0 or n == total:
            logger.info("[%d/%d — %.0f%%] %s — %s", n, total, n / total * 100, pos, country)

    all_jobs = searcher.search_all(progress_callback=progress, positions=positions)
    logger.info("Total raw jobs found: %d", len(all_jobs))

    new_jobs = db.filter_new(all_jobs)
    logger.info("New (not sent before): %d (duplicates: %d)", len(new_jobs), len(all_jobs) - len(new_jobs))

    search_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    subj = datetime.now(timezone.utc).strftime("%b %d, %Y")

    if not new_jobs:
        logger.info("No new jobs this cycle.")
        db.log_run(len(all_jobs), 0, "no_new_jobs")
        if send_telegram_flag and telegram_token and telegram_chat_id:
            _send_tg(telegram_token, telegram_chat_id, [], dry_run)
        if send_email_flag and not dry_run:
            send_email(compose_html_email([], search_date), subj)
        db.close()
        return {"found": len(all_jobs), "new": 0, "status": "no_new_jobs"}

    tel_ok = False
    if send_telegram_flag and telegram_token and telegram_chat_id:
        tel_ok = _send_tg(telegram_token, telegram_chat_id, new_jobs, dry_run)

    email_ok = False
    if dry_run:
        logger.info("DRY RUN (%d jobs):", len(new_jobs))
        for i, j in enumerate(new_jobs[:15], 1):
            logger.info("  %d. %s @ %s — %s — %s", i, j.get("title","?"), j.get("company","?"), j.get("country","?"), j.get("url","")[:80])
        email_ok = True
    elif send_email_flag:
        email_ok = send_email(compose_html_email(new_jobs, search_date), subj)

    if email_ok or tel_ok:
        db.mark_all_sent(new_jobs)
        db.log_run(len(all_jobs), len(new_jobs), "sent")
        logger.info("✅ Pipeline complete: %d new jobs sent.", len(new_jobs))
        status = "sent"
    else:
        db.log_run(len(all_jobs), len(new_jobs), "send_failed")
        logger.error("❌ Notifications FAILED.")
        status = "send_failed"

    db.close()
    return {"found": len(all_jobs), "new": len(new_jobs), "status": status}


def _send_tg(token, chat_id, jobs, dry_run):
    html = compose_telegram_html(jobs)
    if dry_run:
        logger.info("TG DRY RUN:\n%s", html[:400])
        return True
    try:
        for msg in _split(html, 4000):
            r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=15)
            if not r.json().get("ok"):
                logger.error("Telegram: %s", r.json())
                return False
        logger.info("✅ Telegram sent")
        return True
    except Exception as e:
        logger.error("Telegram: %s", e)
        return False


def _split(text, n=4000):
    if len(text) <= n: return [text]
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > n:
            parts.append(cur); cur = line
        else:
            cur += ("\n" + line) if cur else line
    if cur: parts.append(cur)
    return parts


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-email", action="store_true")
    p.add_argument("--no-telegram", action="store_true")
    args = p.parse_args()
    print(json.dumps(run_pipeline(
        send_email_flag=not args.no_email,
        send_telegram_flag=not args.no_telegram,
        dry_run=args.dry_run,
    )))

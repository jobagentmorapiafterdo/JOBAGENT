#!/usr/bin/env python3
# =============================================================================
# Oil & Gas Job Agent — Telegram Bot
# Deploy to Render.com (free) or any free Python host.
# Handles /search, /status, /help commands + sends scheduled results.
# =============================================================================

import os, sys, json, logging, time, threading
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("bot")

from job_searcher import JobSearcher
from database import JobDatabase
from messenger import compose_telegram_html

# ------------------------------------------------------------------
# Configuration from environment
# ------------------------------------------------------------------
TOKEN        = os.getenv("TELEGRAM_BOT_TOKEN", "")
MY_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")    # Authorized chat
API_BASE     = f"https://api.telegram.org/bot{TOKEN}"

from config import POSITIONS, COUNTRIES

# ------------------------------------------------------------------
# Command handlers
# ------------------------------------------------------------------

def cmd_start(chat_id: str):
    send_msg(chat_id,
        "🛢️ <b>Oil & Gas Job Agent</b> is running!\n\n"
        "<b>Commands:</b>\n"
        "/search — Run full search now & email results\n"
        "/search 🇰🇼 Kuwait — Search a specific country\n"
        "/country 🇰🇼 — Quick single-country search\n"
        "/status — Show database stats\n"
        "/help — Show this help\n\n"
        "<b>Auto:</b> Full searches run every <b>Tuesday &amp; Friday</b>. "
        "Results emailed to gregslum@gmail.com."
    )


def cmd_help(chat_id: str):
    send_msg(chat_id,
        "🛢️ <b>Oil & Gas Job Agent — Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/search — Full search (all 14 positions × 50 countries)\n"
        "/search Manager — Search specific position globally\n"
        "/country Norway — Search all positions in one country\n"
        "/status — How many jobs sent so far\n\n"
        "<b>Scheduled:</b> Auto-runs Tue &amp; Fri at 8:00 AM Lagos time.\n"
        "Results sent to: gregslum@gmail.com\n\n"
        "All jobs found are filtered for <b>visa sponsorship</b>."
    )


def cmd_status(chat_id: str):
    try:
        db = JobDatabase("jobs.db")
        total = db.total_sent()
        db.close()
        send_msg(chat_id, f"📊 <b>Job Agent Status</b>\n\nTotal unique jobs sent so far: <b>{total}</b>\n\n14 positions × 50 countries monitored.")
    except Exception as e:
        send_msg(chat_id, f"❌ Error reading database: {e}")


def cmd_search(chat_id: str, args: str = ""):
    """Full search across all positions and countries."""
    send_msg(chat_id, "🔍 <b>Starting full search...</b>\n14 positions × 50 countries = 700 queries.\nThis will take ~25-30 minutes.\nYou'll get results when complete.")

    def run():
        try:
            db = JobDatabase("jobs.db")
            searcher = JobSearcher()

            all_jobs = []
            total = len(POSITIONS) * len(COUNTRIES)
            n = 0

            for pos in POSITIONS:
                for country in COUNTRIES:
                    n += 1
                    try:
                        jobs = searcher.search_single(pos, country)
                        all_jobs.extend(jobs)
                    except Exception as e:
                        logger.warning("Search fail: %s / %s — %s", pos, country, e)
                    time.sleep(2)  # Polite delay

            # Deduplicate
            seen = set()
            unique = []
            for j in all_jobs:
                h = f"{j.get('url','')}|{j.get('title','')}|{j.get('company','')}"
                if h not in seen:
                    seen.add(h)
                    unique.append(j)

            new_jobs = db.filter_new(unique)

            if not new_jobs:
                send_msg(chat_id, f"🔍 Search complete!\n\n❌ No <b>new</b> visa-sponsored jobs found.\n(Found {len(unique)} total, all previously sent.)")
                db.close()
                return

            # Mark as sent
            db.mark_all_sent(new_jobs)
            db.log_run(len(unique), len(new_jobs), "telegram_search")
            db.close()

            # Send results as Telegram messages
            html = compose_telegram_html(new_jobs)
            for chunk in chunk_msg(html):
                send_msg(chat_id, chunk)

        except Exception as e:
            logger.error("Search thread error: %s", e)
            send_msg(chat_id, f"❌ Search failed: {e}")

    threading.Thread(target=run, daemon=True).start()


def cmd_country(chat_id: str, country_name: str):
    """Search all positions in one specific country."""
    if not country_name:
        send_msg(chat_id, "Usage: /country &lt;Country Name&gt;\nExample: /country Norway")
        return

    # Find closest matching country
    match = None
    cn_lower = country_name.strip().lower()
    for c in COUNTRIES:
        if c.lower() == cn_lower:
            match = c
            break
    if not match:
        for c in COUNTRIES:
            if cn_lower in c.lower():
                match = c
                break

    if not match:
        send_msg(chat_id, f"❌ Country '{country_name}' not in my list of 50 monitored countries.\nUse /help to see commands.")
        return

    send_msg(chat_id, f"🔍 Searching all 14 positions in <b>{match}</b>...")

    def run():
        try:
            db = JobDatabase("jobs.db")
            searcher = JobSearcher()
            all_jobs = []

            for pos in POSITIONS:
                try:
                    jobs = searcher.search_single(pos, match)
                    all_jobs.extend(jobs)
                except Exception as e:
                    logger.warning("Fail: %s/%s — %s", pos, match, e)
                time.sleep(2)

            new_jobs = db.filter_new(all_jobs)
            if not new_jobs:
                send_msg(chat_id, f"🔍 <b>{match}</b> — No new visa-sponsored oil & gas jobs found.")
            else:
                db.mark_all_sent(new_jobs)
                html = compose_telegram_html(new_jobs)
                for chunk in chunk_msg(html):
                    send_msg(chat_id, chunk)
            db.log_run(len(all_jobs), len(new_jobs), "telegram_country")
            db.close()
        except Exception as e:
            send_msg(chat_id, f"❌ Search failed: {e}")

    threading.Thread(target=run, daemon=True).start()


# ------------------------------------------------------------------
# Telegram API helpers
# ------------------------------------------------------------------

def send_msg(chat_id: str, text: str):
    """Send a message via Telegram Bot API."""
    try:
        resp = requests.post(
            f"{API_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=15
        )
        if not resp.json().get("ok"):
            logger.error("Telegram send error: %s", resp.json())
    except Exception as e:
        logger.error("Telegram API error: %s", e)


def chunk_msg(text: str, max_len: int = 4000) -> list:
    """Split message at line boundaries."""
    if len(text) <= max_len:
        return [text]
    parts = []
    cur = ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > max_len:
            parts.append(cur)
            cur = line
        else:
            cur += ("\n" + line) if cur else line
    if cur:
        parts.append(cur)
    return parts


# ------------------------------------------------------------------
# Main polling loop
# ------------------------------------------------------------------

def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set! Create a bot at @BotFather.")
        sys.exit(1)

    logger.info("Bot starting. Polling for updates...")
    last_update_id = 0

    # Send startup message
    if MY_CHAT_ID:
        send_msg(MY_CHAT_ID, "✅ Oil & Gas Job Agent bot is online.\nType /help for commands.")

    while True:
        try:
            resp = requests.get(
                f"{API_BASE}/getUpdates",
                params={"offset": last_update_id + 1, "timeout": 30, "allowed_updates": ["message"]},
                timeout=35
            )
            data = resp.json()
            if not data.get("ok"):
                time.sleep(5)
                continue

            for upd in data.get("result", []):
                last_update_id = upd["update_id"]
                msg = upd.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = (msg.get("text") or "").strip()

                if not text:
                    continue

                # Command routing
                if text.startswith("/start"):
                    cmd_start(chat_id)
                elif text.startswith("/help"):
                    cmd_help(chat_id)
                elif text.startswith("/status"):
                    cmd_status(chat_id)
                elif text.startswith("/country "):
                    country = text[len("/country "):].strip()
                    cmd_country(chat_id, country)
                elif text.startswith("/country"):
                    send_msg(chat_id, "Usage: /country Norway\nSearches all positions in one country.")
                elif text.startswith("/search "):
                    # /search with args — could be a position name or just trigger full search
                    arg = text[len("/search "):].strip()
                    cmd_search(chat_id, arg)
                elif text.startswith("/search"):
                    cmd_search(chat_id)
                else:
                    # Unknown — show help
                    cmd_help(chat_id)

        except requests.exceptions.ReadTimeout:
            continue
        except Exception as e:
            logger.error("Polling error: %s", e)
            time.sleep(10)


if __name__ == "__main__":
    main()

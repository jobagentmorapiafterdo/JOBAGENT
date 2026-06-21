#!/usr/bin/env python3
# Oil & Gas Job Agent — Telegram Bot (deploy to Render.com for free)
import os, sys, json, logging, time, threading

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bot")

TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
API     = f"https://api.telegram.org/bot{TOKEN}"

from job_searcher import JobSearcher, search_one
from database import JobDatabase
from messenger import compose_tg, send_telegram
from config import TUE_POSITIONS, FRI_POSITIONS, COUNTRIES, POSITIONS


def _send(chat, text):
    try:
        r = requests.post(f"{API}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=15)
        return r.json().get("ok", False)
    except: return False


def _chunk(text, n=4000):
    if len(text) <= n: return [text]
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur)+len(line)+1 > n: parts.append(cur); cur = line
        else: cur += ("\n"+line) if cur else line
    if cur: parts.append(cur)
    return parts


def cmd_start(chat):
    _send(chat, "🛢️ <b>Oil & Gas Job Agent</b>\n\n"
        "/search — Run full search now & email results\n"
        "/country 🇰🇼 — Search one country\n"
        "/status — Job count\n"
        "/help — Commands")


def cmd_help(chat):
    _send(chat, "🛢️ <b>Commands:</b>\n"
        "/search — Full search (all positions × all countries)\n"
        "/country Norway — Search one country\n"
        "/status — How many jobs sent\n\n"
        "Auto: Tue & Fri 08:00 Lagos → gregslum@gmail.com")


def cmd_status(chat):
    try:
        db = JobDatabase("jobs.db")
        total = db.total(); db.close()
        _send(chat, f"📊 <b>{total}</b> unique jobs sent so far.\n14 positions × 50 countries.")
    except Exception as e:
        _send(chat, f"❌ Error: {e}")


def cmd_search(chat):
    _send(chat, "🔍 Running full search... (7 min)\n350 queries — will notify when done.")
    def _run():
        try:
            db = JobDatabase("jobs.db"); s = JobSearcher()
            all_jobs = s.search_all(positions=POSITIONS)
            new_jobs = db.filter_new(all_jobs)
            if new_jobs:
                db.mark_all(new_jobs)
                tg = compose_tg(new_jobs)
                for c in _chunk(tg): _send(chat, c)
            else:
                _send(chat, "❌ No new visa-sponsored jobs found.")
            db.log(len(all_jobs), len(new_jobs), "tg_search"); db.close()
        except Exception as e:
            _send(chat, f"❌ Error: {e}")
    threading.Thread(target=_run, daemon=True).start()


def cmd_country(chat, name):
    # Find country
    match = None
    nl = name.strip().lower()
    for c in COUNTRIES:
        if c.lower() == nl: match = c; break
    if not match:
        for c in COUNTRIES:
            if nl in c.lower(): match = c; break
    if not match:
        _send(chat, f"❌ '{name}' not found in 50 monitored countries.")
        return

    _send(chat, f"🔍 Searching all 14 positions in <b>{match}</b>...")
    def _run():
        try:
            db = JobDatabase("jobs.db")
            jobs = []
            for pos in POSITIONS:
                try:
                    jobs += search_one(pos, match)
                except: pass
                time.sleep(3)
            new_jobs = db.filter_new(jobs)
            if new_jobs:
                db.mark_all(new_jobs)
                for c in _chunk(compose_tg(new_jobs)):
                    _send(chat, c)
            else:
                _send(chat, f"❌ No new visa-sponsored jobs in {match}.")
            db.log(len(jobs), len(new_jobs), f"tg_country_{match}"); db.close()
        except Exception as e:
            _send(chat, f"❌ Error: {e}")
    threading.Thread(target=_run, daemon=True).start()


def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!"); sys.exit(1)
    logger.info("Bot starting...")
    if CHAT_ID: _send(CHAT_ID, "✅ Oil & Gas Job Agent bot is online.\nType /help for commands.")
    offset = 0
    while True:
        try:
            r = requests.get(f"{API}/getUpdates", params={"offset": offset+1, "timeout": 30}, timeout=35)
            data = r.json()
            if not data.get("ok"): time.sleep(5); continue
            for upd in data.get("result", []):
                offset = upd["update_id"]
                msg = upd.get("message", {}); chat = str(msg.get("chat", {}).get("id", ""))
                text = (msg.get("text") or "").strip()
                if not text: continue
                if text.startswith("/start"): cmd_start(chat)
                elif text.startswith("/help"): cmd_help(chat)
                elif text.startswith("/status"): cmd_status(chat)
                elif text.startswith("/search"): cmd_search(chat)
                elif text.startswith("/country "): cmd_country(chat, text.split(" ",1)[1])
                elif text.startswith("/country"): _send(chat, "Usage: /country Norway")
                else: cmd_help(chat)
        except requests.exceptions.ReadTimeout: continue
        except Exception as e: logger.error("Poll: %s", e); time.sleep(10)


if __name__ == "__main__":
    main()

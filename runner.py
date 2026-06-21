#!/usr/bin/env python3
# Oil & Gas Job Agent — Runner (Tue 7 positions, Fri 7 positions)
import os, json, logging, argparse
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger("runner")

from job_searcher import JobSearcher
from database import JobDatabase
from messenger import send_email, compose_email, send_telegram
from config import TUE_POSITIONS, FRI_POSITIONS, COUNTRIES, RECIPIENT


def get_positions():
    wd = datetime.now().isoweekday()
    if wd == 2: return TUE_POSITIONS, "tuesday"
    if wd == 5: return FRI_POSITIONS, "friday"
    return TUE_POSITIONS + FRI_POSITIONS, "all"


def run(dry=False):
    positions, day = get_positions()
    total = len(positions) * len(COUNTRIES)

    logger.info("=" * 55)
    logger.info("🛢️  Oil & Gas Job Agent — %s (%d pos × %d cnt = %d queries)", day, len(positions), len(COUNTRIES), total)
    logger.info("    Recipient: %s", RECIPIENT)
    logger.info("=" * 55)

    db = JobDatabase("jobs.db")
    s = JobSearcher()

    def prog(n, t, p, c):
        if n % 10 == 0 or n == t:
            logger.info("[%d/%d — %.0f%%] %s — %s", n, t, n/t*100, p, c)

    # Search
    all_jobs = s.search_all(progress=prog, positions=positions)
    logger.info("Raw: %d jobs", len(all_jobs))

    # Filter
    new_jobs = db.filter_new(all_jobs)
    logger.info("New: %d (dup: %d)", len(new_jobs), len(all_jobs) - len(new_jobs))

    date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    subj = datetime.now(timezone.utc).strftime("%b %d, %Y")

    if not new_jobs:
        logger.info("No new jobs")
        db.log(len(all_jobs), 0, "no_new")
        send_telegram([], dry_run=dry)
        if not dry: send_email(compose_email([], date), subj)
        db.close()
        return {"found": len(all_jobs), "new": 0, "status": "no_new"}

    # Telegram
    tg_ok = send_telegram(new_jobs, dry_run=dry)

    # Email
    if dry:
        logger.info("DRY RUN — %d jobs:", len(new_jobs))
        for i, j in enumerate(new_jobs[:15], 1):
            logger.info("  %d. %s @ %s — %s", i, j.get("title","?"), j.get("company","?"), j.get("country","?"))
        email_ok = True
    else:
        email_ok = send_email(compose_email(new_jobs, date), subj)

    if email_ok or tg_ok:
        db.mark_all(new_jobs)
        db.log(len(all_jobs), len(new_jobs), "sent")
        logger.info("✅ Done: %d new jobs sent", len(new_jobs))
    else:
        db.log(len(all_jobs), len(new_jobs), "fail")
        logger.error("❌ Notifications failed")

    db.close()
    return {"found": len(all_jobs), "new": len(new_jobs), "status": "sent"}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-email", action="store_true")
    p.add_argument("--no-tg", action="store_true")
    args = p.parse_args()
    print(json.dumps(run(dry=args.dry_run)))
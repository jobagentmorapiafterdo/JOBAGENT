# =============================================================================
# Oil & Gas Job Agent — Database (SQLite)
# Tracks which jobs were already sent to avoid duplicates.
# =============================================================================

import sqlite3, hashlib, logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class JobDatabase:
    def __init__(self, db_path="jobs.db"):
        self.conn = sqlite3.connect(db_path)
        self._init()

    def _init(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_jobs (
                job_hash TEXT PRIMARY KEY,
                title TEXT, company TEXT, country TEXT, url TEXT,
                sent_at TEXT NOT NULL
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS run_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT NOT NULL, jobs_found INTEGER, jobs_new INTEGER,
                status TEXT, error_message TEXT
            )
        """)
        self.conn.commit()

    def _hash(self, job: dict) -> str:
        return hashlib.sha256(
            f"{job.get('url','')}|{job.get('title','')}|{job.get('company','')}|{job.get('country','')}".encode()
        ).hexdigest()

    def is_sent(self, job: dict) -> bool:
        c = self.conn.execute("SELECT 1 FROM sent_jobs WHERE job_hash=?", (self._hash(job),))
        return c.fetchone() is not None

    def mark_sent(self, job: dict):
        self.conn.execute(
            "INSERT OR IGNORE INTO sent_jobs(job_hash,title,company,country,url,sent_at) VALUES(?,?,?,?,?,?)",
            (self._hash(job), job.get("title",""), job.get("company",""), job.get("country",""), job.get("url",""), datetime.now(timezone.utc).isoformat())
        )
        self.conn.commit()

    def filter_new(self, jobs: list) -> list:
        return [j for j in jobs if not self.is_sent(j)]

    def mark_all_sent(self, jobs: list):
        for j in jobs:
            self.mark_sent(j)

    def log_run(self, found, new, status, error=""):
        self.conn.execute(
            "INSERT INTO run_log(run_at,jobs_found,jobs_new,status,error_message) VALUES(?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), found, new, status, error)
        )
        self.conn.commit()

    def total_sent(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM sent_jobs").fetchone()[0]

    def close(self):
        self.conn.close()
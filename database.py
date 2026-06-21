# Oil & Gas Job Agent — SQLite dedup database
import sqlite3, hashlib, logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class JobDatabase:
    def __init__(self, path="jobs.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sent (
                hash TEXT PRIMARY KEY,
                title TEXT, company TEXT, country TEXT, url TEXT,
                sent_at TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at TEXT, found INTEGER, new INTEGER, status TEXT
            )
        """)
        self.conn.commit()

    def _h(self, job):
        return hashlib.sha256(
            f"{job.get('url','')}|{job.get('title','')}|{job.get('company','')}|{job.get('country','')}".encode()
        ).hexdigest()

    def is_sent(self, job):
        return self.conn.execute("SELECT 1 FROM sent WHERE hash=?", (self._h(job),)).fetchone() is not None

    def mark_sent(self, job):
        self.conn.execute(
            "INSERT OR IGNORE INTO sent(hash,title,company,country,url,sent_at) VALUES(?,?,?,?,?,?)",
            (self._h(job), job.get("title",""), job.get("company",""),
             job.get("country",""), job.get("url",""),
             datetime.now(timezone.utc).isoformat()))

    def filter_new(self, jobs):
        return [j for j in jobs if not self.is_sent(j)]

    def mark_all(self, jobs):
        for j in jobs: self.mark_sent(j)

    def log(self, found, new, status):
        self.conn.execute("INSERT INTO runs(at,found,new,status) VALUES(?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), found, new, status))
        self.conn.commit()

    def total(self):
        return self.conn.execute("SELECT COUNT(*) FROM sent").fetchone()[0]

    def close(self):
        self.conn.close()

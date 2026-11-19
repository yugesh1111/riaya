"""Durable storage for tester feedback in PostgreSQL (DATABASE_URL), so responses survive server restarts and deploys.

Render's free web service starts from a clean disk on every restart; this keeps the usability-test record. Comments
are encrypted with the app key before they are stored. Without DATABASE_URL the app keeps using its local database.
"""
import os

URL = os.environ.get("DATABASE_URL")
COLS = ["id", "ts", "device", "lang", "tried", "sus", "sus_score", "clear", "private_felt", "voice_ok", "would_use", "recommend", "comment"]


def enabled():
    return bool(URL)


def _conn():
    import psycopg  # imported only when a database is configured
    return psycopg.connect(URL, autocommit=True, connect_timeout=10)


def init():
    if not URL:
        return
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS tester_feedback (
            id TEXT PRIMARY KEY, ts DOUBLE PRECISION NOT NULL, device TEXT, lang TEXT, tried TEXT, sus TEXT NOT NULL,
            sus_score DOUBLE PRECISION NOT NULL, clear INTEGER, private_felt INTEGER, voice_ok INTEGER, would_use INTEGER,
            recommend INTEGER, comment BYTEA)""")


def insert(row):
    with _conn() as c:
        c.execute(f"INSERT INTO tester_feedback ({','.join(COLS)}) VALUES ({','.join(['%s'] * len(COLS))})", row)


def rows():
    with _conn() as c:
        cur = c.execute(f"SELECT {','.join(COLS)} FROM tester_feedback ORDER BY ts")
        return [dict(zip(COLS, r)) for r in cur.fetchall()]

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("RIAYA_DB", ROOT / "data" / "app.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, created_at REAL NOT NULL, lang TEXT DEFAULT 'ar');
CREATE TABLE IF NOT EXISTS consents (
  user_id TEXT NOT NULL, purpose TEXT NOT NULL, granted INTEGER NOT NULL, version TEXT NOT NULL, ts REAL NOT NULL);
CREATE TABLE IF NOT EXISTS assessments (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, started_at REAL NOT NULL, completed_at REAL,
  answers BLOB, wearable BLOB, semen BLOB, result BLOB,
  tier TEXT, level TEXT, requires_review INTEGER DEFAULT 0, review_consent INTEGER DEFAULT 0,
  cohort TEXT, simulated INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS referrals (
  id TEXT PRIMARY KEY, assessment_id TEXT NOT NULL, level TEXT NOT NULL, status TEXT NOT NULL,
  created_at REAL NOT NULL, reviewed_at REAL, reviewer TEXT, final_level TEXT, note BLOB,
  booked_at REAL, attended_at REAL, simulated INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS shares (
  code TEXT PRIMARY KEY, assessment_id TEXT NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL,
  revoked INTEGER DEFAULT 0, used_by TEXT);
CREATE TABLE IF NOT EXISTS clinicians (
  username TEXT PRIMARY KEY, salt TEXT NOT NULL, pw_hash TEXT NOT NULL, display_name TEXT);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS audit (
  ts REAL NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT);
CREATE TABLE IF NOT EXISTS events (
  ts REAL NOT NULL, assessment_id TEXT, type TEXT NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY, assessment_id TEXT NOT NULL, sender TEXT NOT NULL, body BLOB NOT NULL, ts REAL NOT NULL, read_at REAL);
CREATE TABLE IF NOT EXISTS partner_links (
  token_hash TEXT PRIMARY KEY, assessment_id TEXT NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL, revoked INTEGER DEFAULT 0, views INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS feedback (
  assessment_id TEXT PRIMARY KEY, trust INTEGER, clarity INTEGER, comfort INTEGER, ts REAL);
CREATE TABLE IF NOT EXISTS lab_results (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, assessment_id TEXT, field TEXT NOT NULL, value REAL NOT NULL,
  extracted_value REAL, collected_on TEXT, created_at REAL NOT NULL, detail BLOB,
  review_status TEXT DEFAULT 'pending', review_note BLOB, reviewed_by TEXT, reviewed_at REAL, original_value REAL);
CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, assessment_id TEXT NOT NULL, status TEXT NOT NULL,
  created_at REAL NOT NULL, start_at REAL, items BLOB NOT NULL, checkins BLOB, reminders INTEGER DEFAULT 0,
  doctor_note BLOB, reviewed_at REAL, reviewer TEXT, stopped_at REAL);
CREATE TABLE IF NOT EXISTS providers (
  id TEXT PRIMARY KEY, name_en TEXT NOT NULL, name_ar TEXT NOT NULL, area TEXT NOT NULL, area_ar TEXT NOT NULL,
  sector TEXT NOT NULL, kinds TEXT NOT NULL, website TEXT NOT NULL, active INTEGER DEFAULT 1,
  confirmed_at REAL, confirmed_by TEXT, confirm_note TEXT);
CREATE TABLE IF NOT EXISTS appointments (
  id TEXT PRIMARY KEY, assessment_id TEXT NOT NULL, provider_id TEXT NOT NULL, status TEXT NOT NULL,
  created_at REAL NOT NULL, updated_at REAL NOT NULL, prefs BLOB, slot_at REAL, place_note TEXT, reason TEXT,
  share_code TEXT, decided_by TEXT, simulated INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS recovery (
  user_id TEXT PRIMARY KEY, code_hash TEXT UNIQUE NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS wa_sessions (
  key TEXT PRIMARY KEY, state BLOB, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sharing (
  user_id TEXT PRIMARY KEY, prefs BLOB NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS consent_receipts (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, ts REAL NOT NULL, recipient TEXT NOT NULL, action TEXT NOT NULL, scope TEXT);
CREATE TABLE IF NOT EXISTS consultations (
  id TEXT PRIMARY KEY, assessment_id TEXT NOT NULL, clinician TEXT NOT NULL, created_at REAL NOT NULL,
  outcome BLOB NOT NULL, followup_at REAL, followup_done_at REAL);
CREATE TABLE IF NOT EXISTS visit_questions (
  assessment_id TEXT PRIMARY KEY, body BLOB NOT NULL, updated_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS finding_reviews (
  id TEXT PRIMARY KEY, assessment_id TEXT NOT NULL, node TEXT NOT NULL, clinician TEXT NOT NULL, verdict TEXT NOT NULL,
  reason TEXT, ts REAL NOT NULL);
CREATE TABLE IF NOT EXISTS visit_feedback (
  assessment_id TEXT PRIMARY KEY, provider_id TEXT NOT NULL, respect INTEGER, privacy INTEGER, explained INTEGER,
  recommend INTEGER, wait_days REAL, ts REAL NOT NULL);
CREATE TABLE IF NOT EXISTS clinic_access (
  token_hash TEXT PRIMARY KEY, code TEXT NOT NULL, assessment_id TEXT NOT NULL, created_at REAL NOT NULL, expires_at REAL NOT NULL);
"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA secure_delete=ON")  # deleted rows are overwritten, not just unlinked
    return con


@contextmanager
def tx():
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


MIGRATIONS = {
    "assessments": [("labs", "BLOB"), ("channel", "TEXT DEFAULT 'web'")],
    "referrals": [("rapid", "INTEGER DEFAULT 0"), ("due_at", "REAL"), ("video_url", "TEXT"), ("handover_at", "REAL"),
                  ("tests_done_at", "REAL"), ("followup_at", "REAL"), ("barrier", "TEXT"), ("self_reported", "INTEGER DEFAULT 0")],
    "messages": [("audio", "BLOB"), ("mime", "TEXT"), ("seconds", "REAL")],
    "sessions": [("last_seen", "REAL")],
    "users": [("sharing_paused", "INTEGER DEFAULT 0"), ("retention_months", "INTEGER"), ("last_active", "REAL"), ("reminders", "INTEGER DEFAULT 1"),
              ("ramadan", "TEXT DEFAULT 'auto'")],
    "shares": [("scope", "TEXT"), ("purpose", "TEXT DEFAULT 'clinic'")],
    "providers": [("phone", "TEXT"), ("whatsapp", "TEXT")],
    "plans": [("wellbeing", "BLOB"), ("restart", "BLOB"), ("last_nudge_at", "REAL")],
}


def init():
    with tx() as c:
        c.executescript(SCHEMA)
        for table, cols in MIGRATIONS.items():
            have = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
            for name, decl in cols:
                if name not in have:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def audit(actor, action, target=None):
    with tx() as c:
        c.execute("INSERT INTO audit VALUES (?,?,?,?)", (time.time(), actor, action, target))


def event(assessment_id, type_, detail=None):
    with tx() as c:
        c.execute("INSERT INTO events VALUES (?,?,?,?)", (time.time(), assessment_id, type_, detail))

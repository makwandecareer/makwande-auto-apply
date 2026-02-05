import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "app.db")

def utc_now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as db:
        # USERS (if you already have this, keep yours — adjust if needed)
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT UNIQUE NOT NULL,
          full_name TEXT,
          password_hash TEXT NOT NULL,
          is_active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL
        )
        """)

        # DOCUMENTS: CV revamps + cover letters history
        db.execute("""
        CREATE TABLE IF NOT EXISTS documents (
          id TEXT PRIMARY KEY,
          user_email TEXT NOT NULL,
          doc_type TEXT NOT NULL,        -- "cv" | "cover_letter"
          title TEXT,
          stored_as TEXT,                -- filename or storage reference
          content TEXT,                  -- optional (if you store text)
          meta_json TEXT,                -- optional JSON
          created_at TEXT NOT NULL
        )
        """)

        # SAVED JOBS
        db.execute("""
        CREATE TABLE IF NOT EXISTS saved_jobs (
          id TEXT PRIMARY KEY,
          user_email TEXT NOT NULL,
          job_id TEXT,
          job_title TEXT,
          company TEXT,
          location TEXT,
          job_url TEXT,
          match_score REAL,
          created_at TEXT NOT NULL
        )
        """)

        # AUTO APPLY RUNS (high level run)
        db.execute("""
        CREATE TABLE IF NOT EXISTS autoapply_runs (
          id TEXT PRIMARY KEY,
          user_email TEXT NOT NULL,
          mode TEXT NOT NULL,            -- "manual" | "scheduled"
          status TEXT NOT NULL,          -- "running" | "complete" | "failed"
          total INTEGER NOT NULL DEFAULT 0,
          success INTEGER NOT NULL DEFAULT 0,
          failed INTEGER NOT NULL DEFAULT 0,
          started_at TEXT NOT NULL,
          finished_at TEXT
        )
        """)

        # AUTO APPLY RUN ITEMS (each job attempt)
        db.execute("""
        CREATE TABLE IF NOT EXISTS autoapply_run_items (
          id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL,
          user_email TEXT NOT NULL,
          job_id TEXT,
          job_title TEXT,
          company TEXT,
          location TEXT,
          job_url TEXT,
          result TEXT NOT NULL,          -- "success" | "failed"
          error TEXT,
          created_at TEXT NOT NULL
        )
        """)

        # AUTO APPLY RULES (one row per user; can expand later)
        db.execute("""
        CREATE TABLE IF NOT EXISTS autoapply_rules (
          user_email TEXT PRIMARY KEY,
          countries_csv TEXT,            -- "South Africa,Lesotho"
          job_titles_csv TEXT,           -- "HR Officer,Data Analyst"
          keywords_csv TEXT,             -- "payroll,labour relations"
          blacklist_companies_csv TEXT,  -- "CompanyA,CompanyB"
          min_match_score REAL DEFAULT 70,
          updated_at TEXT NOT NULL
        )
        """)

        # SUBSCRIPTIONS
        db.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
          user_email TEXT PRIMARY KEY,
          plan_code TEXT NOT NULL,       -- e.g. "PRO_MONTHLY"
          status TEXT NOT NULL,          -- "active" | "inactive" | "past_due"
          paystack_customer_code TEXT,
          paystack_subscription_code TEXT,
          current_period_end TEXT,
          updated_at TEXT NOT NULL
        )
        """)

        # PAYMENTS LOG
        db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
          reference TEXT PRIMARY KEY,
          user_email TEXT NOT NULL,
          amount_kobo INTEGER NOT NULL,
          currency TEXT NOT NULL,
          status TEXT NOT NULL,          -- "initiated" | "success" | "failed"
          gateway_response TEXT,
          created_at TEXT NOT NULL
        )
        """)

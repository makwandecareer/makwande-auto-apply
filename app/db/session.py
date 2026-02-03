import os
import psycopg
from psycopg.rows import dict_row

def _normalize_db_url(url: str) -> str:
    # Render often gives postgres://... which psycopg understands, but normalize anyway
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url

def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")

    db_url = _normalize_db_url(db_url)

    # autocommit=False so we control commits
    return psycopg.connect(db_url, row_factory=dict_row)

def init_db():
    # Create tables if not exist
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """)
        conn.commit()

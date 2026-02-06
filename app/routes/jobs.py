"""
jobs.py — FastAPI router for:
- GET  /api/jobs         (filterable job list)
- POST /api/match_jobs   (optional matching for results.html)

This module is designed to be "safe to include" in main.py and uses SQLite without SQLAlchemy.
It will auto-create a JOBS table if it doesn't exist.

Expected frontend query params (jobs.html):
  q, country, location, company, limit

Matching endpoint accepts multipart/form-data:
  - cv_file (optional)
  - target_role (optional)
  - jobs (optional JSON list from frontend)

If "jobs" is provided, matching will run on that list.
If "jobs" is not provided, it will match against the DB job list.

Match scoring is a lightweight keyword similarity (no external ML libs).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

router = APIRouter(prefix="/api", tags=["jobs"])

# -------------------------
# SQLite setup
# -------------------------
DEFAULT_DB_PATH = os.getenv("SQLITE_DB_PATH", "data.sqlite3")


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_jobs_db() -> None:
    """Call this once at startup (optional). Safe to call multiple times."""
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS JOBS (
              id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              company TEXT NOT NULL,
              location TEXT NOT NULL,
              country TEXT NOT NULL,
              url TEXT,
              description TEXT,
              post_advertised_date TEXT,
              closing_date TEXT,
              created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON JOBS(company)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_location ON JOBS(location)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_country ON JOBS(country)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_title ON JOBS(title)")


# -------------------------
# Utilities
# -------------------------
_WORD_RE = re.compile(r"[a-z0-9]+")


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _clean(s: Optional[str]) -> str:
    return (s or "").strip()


def _tokenize(text: str) -> List[str]:
    text = text.lower()
    return _WORD_RE.findall(text)


def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def _score_job(job: Dict[str, Any], profile_text: str) -> float:
    """
    Lightweight similarity score (0..100):
      - compares profile_text vs job title + company + location + description
    """
    job_text = " ".join(
        [
            _clean(job.get("title")),
            _clean(job.get("company")),
            _clean(job.get("location")),
            _clean(job.get("description")),
        ]
    )
    a = _tokenize(profile_text)
    b = _tokenize(job_text)
    base = _jaccard(a, b) * 100.0

    # Slightly reward title matches
    title_tokens = _tokenize(_clean(job.get("title")))
    bonus = _jaccard(a, title_tokens) * 15.0

    score = max(0.0, min(100.0, base + bonus))
    return score


def _row_to_job(r: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": r["id"],
        "title": r["title"],
        "company": r["company"],
        "location": r["location"],
        "country": r["country"],
        "url": r["url"] or "",
        "description": r["description"] or "",
        "post_advertised_date": r["post_advertised_date"] or "",
        "closing_date": r["closing_date"] or "",
    }


def _apply_filters_sql(
    q: str,
    country: str,
    location: str,
    company: str,
) -> Tuple[str, List[Any]]:
    where = []
    params: List[Any] = []

    if q:
        # Match title/description/company/location
        where.append(
            "(LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(company) LIKE ? OR LOWER(location) LIKE ?)"
        )
        like = f"%{q.lower()}%"
        params.extend([like, like, like, like])

    if country:
        where.append("LOWER(country) = ?")
        params.append(country.lower())

    if location:
        where.append("LOWER(location) LIKE ?")
        params.append(f"%{location.lower()}%")

    if company:
        where.append("LOWER(company) LIKE ?")
        params.append(f"%{company.lower()}%")

    sql_where = (" WHERE " + " AND ".join(where)) if where else ""
    return sql_where, params


# -------------------------
# Routes
# -------------------------
@router.get("/jobs")
def get_jobs(
    q: str = Query(default="", description="Search across title/company/location/description"),
    country: str = Query(default="", description="Exact country match"),
    location: str = Query(default="", description="Location contains"),
    company: str = Query(default="", description="Company contains"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    """
    Returns: { "jobs": [...], "count": N }
    """
    init_jobs_db()

    q = _clean(q)
    country = _clean(country)
    location = _clean(location)
    company = _clean(company)

    where_sql, params = _apply_filters_sql(q, country, location, company)

    with _db() as conn:
        # Count first
        count_row = conn.execute(
            f"SELECT COUNT(*) AS c FROM JOBS{where_sql}",
            params,
        ).fetchone()
        total = int(count_row["c"]) if count_row else 0

        rows = conn.execute(
            f"""
            SELECT id, title, company, location, country, url, description, post_advertised_date, closing_date
            FROM JOBS
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset],
        ).fetchall()

    return {"jobs": [_row_to_job(r) for r in rows], "count": total}


@router.post("/match_jobs")
async def match_jobs(
    cv_file: Optional[UploadFile] = File(default=None),
    target_role: str = Form(default=""),
    jobs: str = Form(default=""),
) -> Dict[str, Any]:
    """
    Matching endpoint used by jobs.html.
    Returns: { "results": [ ...jobs_with_match_score... ] }

    Input:
      - cv_file: optional (pdf/doc/docx/txt). We only read text for .txt safely here.
      - target_role: optional short string
      - jobs: optional JSON list (string). If provided, we match against this list.
    """
    init_jobs_db()

    # Build "profile_text" from target_role + (optional) CV txt content
    profile_parts = []
    if target_role.strip():
        profile_parts.append(target_role.strip())

    # We do a SAFE read:
    # - If it's .txt, read as text
    # - Otherwise, we ignore content (no OCR / no doc parsing here)
    if cv_file is not None:
        filename = (cv_file.filename or "").lower()
        if filename.endswith(".txt"):
            raw = await cv_file.read()
            try:
                profile_parts.append(raw.decode("utf-8", errors="ignore"))
            except Exception:
                pass

    profile_text = "\n".join(profile_parts).strip()
    if not profile_text:
        raise HTTPException(
            status_code=400,
            detail="Provide target_role and/or a .txt cv_file so we can compute matching.",
        )

    # Get candidate jobs
    job_list: List[Dict[str, Any]] = []

    if jobs.strip():
        try:
            parsed = json.loads(jobs)
            if not isinstance(parsed, list):
                raise ValueError("jobs must be a JSON list")
            # Normalize minimal fields the frontend expects
            for j in parsed:
                if isinstance(j, dict):
                    job_list.append(
                        {
                            "id": str(j.get("id") or j.get("job_id") or j.get("_id") or ""),
                            "title": _clean(j.get("title") or j.get("job_title") or "Untitled role"),
                            "company": _clean(j.get("company") or j.get("employer") or "Unknown"),
                            "location": _clean(j.get("location") or j.get("city") or j.get("country") or "Unknown"),
                            "url": _clean(j.get("url") or j.get("apply_url") or j.get("link") or ""),
                            "description": _clean(j.get("description") or j.get("summary") or ""),
                            "post_advertised_date": _clean(j.get("post_advertised_date") or j.get("advertised_date") or j.get("posted_date") or ""),
                            "closing_date": _clean(j.get("closing_date") or j.get("close_date") or ""),
                        }
                    )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid jobs JSON: {e}")

    else:
        # Match against DB jobs (most recent 500 to keep it fast)
        with _db() as conn:
            rows = conn.execute(
                """
                SELECT id, title, company, location, country, url, description, post_advertised_date, closing_date
                FROM JOBS
                ORDER BY created_at DESC
                LIMIT 500
                """
            ).fetchall()
        job_list = [_row_to_job(r) for r in rows]

    # Score and sort
    scored = []
    for j in job_list:
        score = _score_job(j, profile_text)
        out = dict(j)
        out["match_score"] = round(score, 2)
        scored.append(out)

    scored.sort(key=lambda x: x.get("match_score", 0.0), reverse=True)

    return {"results": scored}


# -------------------------
# Optional helper: insert jobs (for your scraper/admin pipeline)
# -------------------------
def upsert_jobs(jobs: List[Dict[str, Any]]) -> int:
    """
    Insert/update jobs into SQLite.
    Each job dict should include:
      id, title, company, location, country, url, description, post_advertised_date, closing_date
    Returns number of rows upserted.
    """
    init_jobs_db()

    now = _now_iso()
    count = 0

    with _db() as conn:
        for j in jobs:
            job_id = _clean(str(j.get("id") or j.get("job_id") or j.get("_id") or ""))
            if not job_id:
                continue

            conn.execute(
                """
                INSERT INTO JOBS (
                  id, title, company, location, country, url, description,
                  post_advertised_date, closing_date, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  title=excluded.title,
                  company=excluded.company,
                  location=excluded.location,
                  country=excluded.country,
                  url=excluded.url,
                  description=excluded.description,
                  post_advertised_date=excluded.post_advertised_date,
                  closing_date=excluded.closing_date
                """,
                (
                    job_id,
                    _clean(j.get("title")),
                    _clean(j.get("company")),
                    _clean(j.get("location")),
                    _clean(j.get("country") or "South Africa"),
                    _clean(j.get("url")),
                    _clean(j.get("description")),
                    _clean(j.get("post_advertised_date")),
                    _clean(j.get("closing_date")),
                    now,
                ),
            )
            count += 1

    return count

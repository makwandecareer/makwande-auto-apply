from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple

import requests

# If your utils has clean_text, we'll use it; otherwise fallback safely.
try:
    from app.core.utils import clean_text  # type: ignore
except Exception:
    def clean_text(s: str) -> str:
        return " ".join((s or "").split())


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str = ""


ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "za")  # optional


def fetch_jobs_adzuna(query: str, limit: int = 50) -> List[Job]:
    """
    Cloud-safe job fetching via Adzuna API.
    Uses ZA by default (ADZUNA_COUNTRY=za). Works well on Render.
    """
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []

    # Adzuna caps results_per_page; keep within sane bounds.
    limit = max(1, min(int(limit), 50))

    url = f"https://api.adzuna.com/v1/api/jobs/{ADZUNA_COUNTRY}/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": limit,
        "what": query,
        "content-type": "application/json",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    data = r.json()
    out: List[Job] = []

    for item in data.get("results", []) or []:
        title = clean_text(item.get("title", ""))
        company = clean_text((item.get("company") or {}).get("display_name", ""))
        location = clean_text((item.get("location") or {}).get("display_name", ""))
        link = item.get("redirect_url", "") or item.get("adref", "")
        desc = clean_text(item.get("description", "") or "")

        if not title or not link:
            continue

        out.append(
            Job(
                title=title,
                company=company or "Unknown",
                location=location or "Unknown",
                url=link,
                source="adzuna",
                description=desc,
            )
        )

    return out


def fetch_all(query: str, limit: int = 50) -> Tuple[List[Job], List[str]]:
    """
    Returns (jobs, errors). Keep this signature stable for app.main.
    """
    errors: List[str] = []
    jobs: List[Job] = []

    try:
        jobs.extend(fetch_jobs_adzuna(query=query, limit=limit))
    except Exception as e:
        errors.append(f"adzuna failed: {e}")

    return jobs, errors


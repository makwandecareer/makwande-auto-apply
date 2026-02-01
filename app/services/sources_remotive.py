from __future__ import annotations

from dataclasses import dataclass
from typing import List
import requests


@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str = ""


def fetch_jobs_remotive(query: str, limit: int = 50) -> List[Job]:
    """
    Remotive public API (remote jobs).
    Docs-style endpoint: https://remotive.com/api/remote-jobs
    """
    limit = max(1, min(int(limit), 100))

    url = "https://remotive.com/api/remote-jobs"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    jobs = []
    q = (query or "").strip().lower()

    for item in (data.get("jobs") or []):
        title = (item.get("title") or "").strip()
        company = (item.get("company_name") or "").strip()
        location = (item.get("candidate_required_location") or "Remote").strip()
        link = (item.get("url") or "").strip()
        desc = (item.get("description") or "").strip()

        if not title or not link:
            continue

        # Lightweight filtering by query keywords
        hay = f"{title} {company} {location}".lower()
        if q and q not in hay:
            # allow partial matches by splitting query into words
            words = [w for w in q.split() if len(w) > 2]
            if words and not any(w in hay for w in words):
                continue

        jobs.append(
            Job(
                title=title,
                company=company or "Unknown",
                location=location or "Remote",
                url=link,
                source="remotive",
                description=desc,
            )
        )

        if len(jobs) >= limit:
            break

    return jobs

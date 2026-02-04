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


def fetch_lever_board(company_slug: str, limit: int = 50) -> List[Job]:
    """
    Lever jobs endpoint:
    https://api.lever.co/v0/postings/{company_slug}?mode=json
    """
    limit = max(1, min(int(limit), 200))
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"

    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    jobs: List[Job] = []
    company_name = company_slug.replace("-", " ").title()

    for item in (data or []):
        title = (item.get("text") or "").strip()
        location = ((item.get("categories") or {}).get("location") or "Unknown").strip()
        link = (item.get("hostedUrl") or "").strip()

        if not title or not link:
            continue

        jobs.append(
            Job(
                title=title,
                company=company_name,
                location=location,
                url=link,
                source="lever",
                description="",
            )
        )

        if len(jobs) >= limit:
            break

    return jobs


def filter_jobs(jobs: List[Job], query: str, limit: int) -> List[Job]:
    q = (query or "").strip().lower()
    if not q:
        return jobs[:limit]

    words = [w for w in q.split() if len(w) > 2]
    out = []
    for j in jobs:
        hay = f"{j.title} {j.company} {j.location}".lower()
        if q in hay or any(w in hay for w in words):
            out.append(j)
        if len(out) >= limit:
            break
    return out

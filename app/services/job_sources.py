from __future__ import annotations

from dataclasses import dataclass
from typing import List
import requests
from bs4 import BeautifulSoup

from app.core.utils import clean_text

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0 Safari/537.36"
}

@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    source: str

def fetch_jobs_remotive(query: str = "engineer", limit: int = 50) -> List[Job]:
    """Remotive public JSON API."""
    api = f"https://remotive.com/api/remote-jobs?search={query}"
    r = requests.get(api, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    jobs: List[Job] = []
    for item in data.get("jobs", [])[:limit]:
        jobs.append(
            Job(
                title=clean_text(item.get("title", "")),
                company=clean_text(item.get("company_name", "")),
                location=clean_text(item.get("candidate_required_location", "Remote")),
                url=item.get("url", ""),
                source="remotive",
            )
        )
    return jobs

def fetch_jobs_weworkremotely(query: str = "engineer", limit: int = 50) -> List[Job]:
    """Light scrape. If selectors change, update them."""
    url = f"https://weworkremotely.com/remote-jobs/search?term={query}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    jobs: List[Job] = []

    for li in soup.select("section.jobs li")[:limit]:
        a = li.select_one("a")
        if not a or not a.get("href"):
            continue

        title_el = li.select_one("span.title")
        company_el = li.select_one("span.company")
        region_el = li.select_one("span.region")

        title = clean_text(title_el.get_text()) if title_el else ""
        company = clean_text(company_el.get_text()) if company_el else ""
        location = clean_text(region_el.get_text()) if region_el else "Remote"

        if not title or title.lower() == "view all":
            continue

        jobs.append(
            Job(
                title=title,
                company=company,
                location=location,
                url="https://weworkremotely.com" + a["href"],
                source="weworkremotely",
            )
        )

    return jobs

def fetch_all(query: str, limit: int):
    jobs = []
    errors = []

    try:
        jobs += fetch_jobs_remotive(query=query, limit=limit)
    except Exception as e:
        errors.append(f"remotive failed: {e}")

    try:
        jobs += fetch_jobs_weworkremotely(query=query, limit=limit)
    except Exception as e:
        errors.append(f"weworkremotely failed: {e}")

    return jobs, errors


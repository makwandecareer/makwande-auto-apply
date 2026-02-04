from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import List, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# Local source modules
from app.services.sources_remotive import fetch_jobs_remotive, Job as RemotiveJob
from app.services.sources_greenhouse import fetch_greenhouse_board, filter_jobs as filter_greenhouse, Job as GreenhouseJob
from app.services.sources_lever import fetch_lever_board, filter_jobs as filter_lever, Job as LeverJob


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
ADZUNA_COUNTRY = os.getenv("ADZUNA_COUNTRY", "za")

# Provide comma-separated board tokens in Render env vars
# Example:
# GREENHOUSE_BOARDS=shopify,airbnb
# LEVER_BOARDS=netflix,spotify
GREENHOUSE_BOARDS = [x.strip() for x in (os.getenv("GREENHOUSE_BOARDS", "")).split(",") if x.strip()]
LEVER_BOARDS = [x.strip() for x in (os.getenv("LEVER_BOARDS", "")).split(",") if x.strip()]


def _clean(s: str) -> str:
    return " ".join((s or "").split()).strip()


def _normalize_key(title: str, company: str, location: str) -> str:
    """
    Dedup key across sources.
    """
    def norm(x: str) -> str:
        x = (x or "").lower()
        x = re.sub(r"[^a-z0-9\s]+", " ", x)
        x = re.sub(r"\s+", " ", x).strip()
        return x

    return f"{norm(title)}|{norm(company)}|{norm(location)}"


def fetch_jobs_adzuna(query: str, limit: int = 50) -> List[Job]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []

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
    for item in (data.get("results") or []):
        title = _clean(item.get("title", ""))
        company = _clean((item.get("company") or {}).get("display_name", "")) or "Unknown"
        location = _clean((item.get("location") or {}).get("display_name", "")) or "Unknown"
        link = (item.get("redirect_url", "") or item.get("adref", "") or "").strip()
        desc = _clean(item.get("description", "") or "")

        if not title or not link:
            continue

        out.append(Job(title=title, company=company, location=location, url=link, source="adzuna", description=desc))

    return out


def _convert_jobs(items: List[object]) -> List[Job]:
    out: List[Job] = []
    for it in items:
        # they all have same shape (title, company, location, url, source, description)
        out.append(Job(
            title=getattr(it, "title", ""),
            company=getattr(it, "company", ""),
            location=getattr(it, "location", ""),
            url=getattr(it, "url", ""),
            source=getattr(it, "source", ""),
            description=getattr(it, "description", "") or "",
        ))
    return out


def fetch_all(query: str, limit: int = 50) -> Tuple[List[Job], List[str]]:
    """
    Returns (jobs, errors).
    Multi-source + parallel fetching.
    """
    errors: List[str] = []
    jobs: List[Job] = []

    # Per-source limit: keep it balanced
    per_source = max(10, min(int(limit), 50))

    tasks = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        # Adzuna
        tasks[ex.submit(fetch_jobs_adzuna, query, per_source)] = "adzuna"

        # Remotive (remote)
        tasks[ex.submit(fetch_jobs_remotive, query, per_source)] = "remotive"

        # Greenhouse boards (public ATS job boards)
        for token in GREENHOUSE_BOARDS[:10]:  # limit boards to avoid huge slow calls
            tasks[ex.submit(fetch_greenhouse_board, token, 200)] = f"greenhouse:{token}"

        # Lever boards
        for slug in LEVER_BOARDS[:10]:
            tasks[ex.submit(fetch_lever_board, slug, 200)] = f"lever:{slug}"

        results: Dict[str, List[Job]] = {}

        for fut in as_completed(tasks):
            label = tasks[fut]
            try:
                raw = fut.result()
                # Greenhouse/Lever returns their own Job dataclass; convert them
                if label.startswith("greenhouse:"):
                    g_jobs = _convert_jobs(raw)
                    results[label] = filter_greenhouse(g_jobs, query, per_source)
                elif label.startswith("lever:"):
                    l_jobs = _convert_jobs(raw)
                    results[label] = filter_lever(l_jobs, query, per_source)
                else:
                    results[label] = raw
            except Exception as e:
                errors.append(f"{label} failed: {e}")

    # Merge
    merged: List[Job] = []
    for _, arr in results.items():
        merged.extend(arr)

    # Deduplicate
    seen = set()
    deduped: List[Job] = []
    for j in merged:
        key = _normalize_key(j.title, j.company, j.location)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)

    # Return top N (your matcher will re-rank anyway)
    return deduped[: max(1, int(limit))], errors

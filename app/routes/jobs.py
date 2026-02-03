import os
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/jobs", tags=["Jobs"])

# -----------------------------
# Simple in-memory cache
# -----------------------------
_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = int(os.getenv("JOBS_CACHE_TTL", "120"))  # 2 min default

def _cache_get(key: str):
    item = _CACHE.get(key)
    if not item:
        return None
    if time.time() - item["ts"] > CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return item["value"]

def _cache_set(key: str, value: Any):
    _CACHE[key] = {"ts": time.time(), "value": value}

# -----------------------------
# Normalization helpers
# -----------------------------
def _safe_str(x) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None

def _mk_job(
    *,
    source: str,
    id: str,
    title: str,
    company: str,
    location: str,
    country: Optional[str] = None,
    remote: Optional[bool] = None,
    job_type: Optional[str] = None,
    posted_at: Optional[str] = None,
    salary_min: Optional[float] = None,
    salary_max: Optional[float] = None,
    salary_currency: Optional[str] = None,
    description: Optional[str] = None,
    apply_url: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "source": source,
        "id": id,
        "title": title,
        "company": company,
        "location": location,
        "country": country,
        "remote": remote,
        "job_type": job_type,
        "posted_at": posted_at,
        "salary": {
            "min": salary_min,
            "max": salary_max,
            "currency": salary_currency,
        },
        "description": description,
        "apply_url": apply_url,
        "tags": tags or [],
    }

def _dedupe(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # unique by source+id OR apply_url if present
    seen = set()
    out = []
    for j in jobs:
        k = f'{j.get("source")}::{j.get("id")}::{j.get("apply_url")}'
        if k in seen:
            continue
        seen.add(k)
        out.append(j)
    return out

# -----------------------------
# Source: Adzuna
# -----------------------------
async def _fetch_adzuna(q: str, country: str, page: int, limit: int) -> List[Dict[str, Any]]:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []

    # Adzuna country codes: za, gb, us, etc.
    country = (country or "za").lower()

    # Adzuna uses 1-based page number
    adz_page = max(1, page)

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": min(max(limit, 1), 50),
        "what": q,
        "content-type": "application/json",
    }

    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{adz_page}?" + urlencode(params)

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return []
        data = r.json()

    results = data.get("results", []) or []
    jobs: List[Dict[str, Any]] = []
    for it in results:
        title = _safe_str(it.get("title")) or "Untitled"
        company = _safe_str((it.get("company") or {}).get("display_name")) or "Unknown"
        loc = _safe_str((it.get("location") or {}).get("display_name")) or "Unknown"
        created = _safe_str(it.get("created"))
        desc = _safe_str(it.get("description"))
        apply_url = _safe_str(it.get("redirect_url")) or _safe_str(it.get("adref"))
        job_id = _safe_str(it.get("id")) or apply_url or f"adzuna-{hash(title+company+loc)}"

        salary_min = it.get("salary_min")
        salary_max = it.get("salary_max")
        salary_currency = _safe_str(it.get("salary_currency"))

        # Adzuna doesn't consistently tell remote/hybrid
        jobs.append(
            _mk_job(
                source="adzuna",
                id=str(job_id),
                title=title,
                company=company,
                location=loc,
                country=country.upper(),
                remote=None,
                job_type=_safe_str(it.get("contract_time")) or _safe_str(it.get("contract_type")),
                posted_at=created,
                salary_min=float(salary_min) if salary_min is not None else None,
                salary_max=float(salary_max) if salary_max is not None else None,
                salary_currency=salary_currency,
                description=desc[:2000] if desc else None,
                apply_url=apply_url,
                tags=[],
            )
        )
    return jobs

# -----------------------------
# Source: Remotive (Remote jobs)
# -----------------------------
async def _fetch_remotive(q: str, page: int, limit: int) -> List[Dict[str, Any]]:
    # Remotive is free and public
    # API: https://remotive.com/api/remote-jobs?search=python
    params = {"search": q} if q else {}
    url = "https://remotive.com/api/remote-jobs"
    if params:
        url += "?" + urlencode(params)

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return []
        data = r.json()

    items = data.get("jobs", []) or []

    # paginate ourselves
    start = max(0, (page - 1) * limit)
    end = start + limit
    items = items[start:end]

    jobs: List[Dict[str, Any]] = []
    for it in items:
        title = _safe_str(it.get("title")) or "Untitled"
        company = _safe_str(it.get("company_name")) or "Unknown"
        loc = _safe_str(it.get("candidate_required_location")) or "Remote"
        posted = _safe_str(it.get("publication_date"))
        desc = _safe_str(it.get("description"))
        apply_url = _safe_str(it.get("url"))
        job_id = _safe_str(it.get("id")) or apply_url or f"remotive-{hash(title+company)}"

        jobs.append(
            _mk_job(
                source="remotive",
                id=str(job_id),
                title=title,
                company=company,
                location=loc,
                country=None,
                remote=True,
                job_type=_safe_str(it.get("job_type")),
                posted_at=posted,
                salary_min=None,
                salary_max=None,
                salary_currency=None,
                description=desc[:2000] if desc else None,
                apply_url=apply_url,
                tags=it.get("tags") or [],
            )
        )
    return jobs

# -----------------------------
# Source: Greenhouse boards
# -----------------------------
async def _fetch_greenhouse(q: str, page: int, limit: int) -> List[Dict[str, Any]]:
    boards_csv = os.getenv("GREENHOUSE_BOARDS", "").strip()
    if not boards_csv:
        return []

    boards = [b.strip() for b in boards_csv.split(",") if b.strip()]
    if not boards:
        return []

    q_lower = (q or "").lower().strip()

    async with httpx.AsyncClient(timeout=20) as client:
        all_jobs: List[Dict[str, Any]] = []
        for board in boards:
            url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
            r = await client.get(url)
            if r.status_code != 200:
                continue
            data = r.json()
            items = data.get("jobs", []) or []
            for it in items:
                title = _safe_str(it.get("title")) or "Untitled"
                # filter by q
                if q_lower and q_lower not in title.lower():
                    continue

                job_id = _safe_str(it.get("id")) or f"gh-{board}-{hash(title)}"
                loc = _safe_str((it.get("location") or {}).get("name")) or "Unknown"
                posted = _safe_str(it.get("updated_at")) or _safe_str(it.get("created_at"))
                apply_url = _safe_str(it.get("absolute_url"))
                desc = _safe_str(it.get("content"))

                all_jobs.append(
                    _mk_job(
                        source="greenhouse",
                        id=str(job_id),
                        title=title,
                        company=board,
                        location=loc,
                        country=None,
                        remote=None,
                        job_type=None,
                        posted_at=posted,
                        description=(desc[:2000] if desc else None),
                        apply_url=apply_url,
                        tags=[],
                    )
                )

    # paginate ourselves
    start = max(0, (page - 1) * limit)
    end = start + limit
    return all_jobs[start:end]

# -----------------------------
# Source: Lever companies
# -----------------------------
async def _fetch_lever(q: str, page: int, limit: int) -> List[Dict[str, Any]]:
    companies_csv = os.getenv("LEVER_COMPANIES", "").strip()
    if not companies_csv:
        return []

    companies = [c.strip() for c in companies_csv.split(",") if c.strip()]
    if not companies:
        return []

    q_lower = (q or "").lower().strip()

    async with httpx.AsyncClient(timeout=20) as client:
        all_jobs: List[Dict[str, Any]] = []
        for comp in companies:
            # Lever postings endpoint
            url = f"https://api.lever.co/v0/postings/{comp}?mode=json"
            r = await client.get(url)
            if r.status_code != 200:
                continue
            items = r.json() or []
            for it in items:
                title = _safe_str(it.get("text")) or "Untitled"
                if q_lower and q_lower not in title.lower():
                    continue

                job_id = _safe_str(it.get("id")) or f"lever-{comp}-{hash(title)}"
                loc = _safe_str(it.get("categories", {}).get("location")) or "Unknown"
                apply_url = _safe_str(it.get("hostedUrl")) or _safe_str(it.get("applyUrl"))
                posted = _safe_str(it.get("createdAt"))
                desc = _safe_str(it.get("descriptionPlain")) or _safe_str(it.get("description"))

                all_jobs.append(
                    _mk_job(
                        source="lever",
                        id=str(job_id),
                        title=title,
                        company=comp,
                        location=loc,
                        country=None,
                        remote=("remote" in loc.lower()) if loc else None,
                        job_type=_safe_str(it.get("categories", {}).get("commitment")),
                        posted_at=posted,
                        description=desc[:2000] if desc else None,
                        apply_url=apply_url,
                        tags=[t.get("text") for t in (it.get("tags") or []) if isinstance(t, dict) and t.get("text")],
                    )
                )

    # paginate ourselves
    start = max(0, (page - 1) * limit)
    end = start + limit
    return all_jobs[start:end]

# -----------------------------
# Public endpoint
# -----------------------------
@router.get("/search")
async def search_jobs(
    q: str = Query(default="", description="Search keywords, e.g. 'chemical engineer'"),
    country: str = Query(default="za", description="Adzuna country code e.g. za, us, gb"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    source: str = Query(default="all", description="all|adzuna|remotive|greenhouse|lever"),
    remote_only: bool = Query(default=False),
):
    cache_key = f"jobs::{q}::{country}::{page}::{limit}::{source}::{remote_only}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    src = source.lower().strip()
    jobs: List[Dict[str, Any]] = []

    try:
        if src in ("all", "adzuna"):
            jobs.extend(await _fetch_adzuna(q=q, country=country, page=page, limit=limit))
        if src in ("all", "remotive"):
            jobs.extend(await _fetch_remotive(q=q, page=page, limit=limit))
        if src in ("all", "greenhouse"):
            jobs.extend(await _fetch_greenhouse(q=q, page=page, limit=limit))
        if src in ("all", "lever"):
            jobs.extend(await _fetch_lever(q=q, page=page, limit=limit))
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Jobs provider timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jobs provider error: {str(e)}")

    # filters
    if remote_only:
        jobs = [j for j in jobs if j.get("remote") is True]

    jobs = _dedupe(jobs)

    payload = {
        "success": True,
        "query": {
            "q": q,
            "country": country,
            "page": page,
            "limit": limit,
            "source": source,
            "remote_only": remote_only,
        },
        "count": len(jobs),
        "jobs": jobs,
    }

    _cache_set(cache_key, payload)
    return payload

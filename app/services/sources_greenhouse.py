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


def fetch_greenhouse_board(board_token: str, limit: int = 50) -> List[Job]:
    """
    Fetch all jobs from a Greenhouse job board:
    https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
    """
    limit = max(1, min(int(limit), 200))
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    jobs: List[Job] = []
    company_name = board_token.replace("-", " ").title()

    for item in (data.get("jobs") or []):
        title = (item.get("title") or "").strip()
        location = ((item.get("location") or {}).get("name") or "Unknown").strip()
        link = (item.get("absolute_url") or "").strip()

        if not title or not link:
            continue

        jobs.append(
            Job(
                title=title,
                company=company_name,
                location=location,
                url=link,
                source="greenhouse",
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
    
from fastapi import HTTPException
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")  # IMPORTANT

def get_password_hash(password: str) -> str:
    if not isinstance(password, str):
        raise HTTPException(status_code=400, detail="Password must be a string")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

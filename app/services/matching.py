from __future__ import annotations

from dataclasses import asdict
from typing import List, Dict, Any
import pandas as pd

from app.core.utils import tokenize
from app.services.job_sources import Job

def score_job(cv_text: str, job: Job) -> Dict[str, Any]:
    """Simple overlap score. Replace with embeddings later."""
    cv_tokens = tokenize(cv_text)
    job_text = f"{job.title} {job.company} {job.location}"
    job_tokens = tokenize(job_text)

    if not job_tokens:
        score = 0.0
        overlap = set()
    else:
        overlap = cv_tokens.intersection(job_tokens)
        score = round(len(overlap) / max(len(job_tokens), 1) * 100, 2)

    row = asdict(job)
    row["match_score"] = score
    row["overlap_keywords"] = ", ".join(sorted(list(overlap))[:25])
    return row

def match_jobs(cv_text: str, jobs: List[Job]) -> pd.DataFrame:
    rows = [score_job(cv_text, j) for j in jobs]
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("match_score", ascending=False).reset_index(drop=True)
    return df

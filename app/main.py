<<<<<<< HEAD
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.services.cv_parse import parse_cv
from app.services.job_sources import fetch_all
from app.services.matching import match_jobs
from app.services.cover_letter import can_generate, generate_cover_letter

# ---------------------------------------------------------
# Paths / storage
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# In-memory CV store (MVP)
CV_STORE: dict[str, str] = {}

# ---------------------------------------------------------
# App
# ---------------------------------------------------------
app = FastAPI(title=getattr(settings, "app_name", "Auto Apply"))


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _safe_get(row: Dict[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


def _df_to_rows(df: pd.DataFrame, max_rows: int = 100) -> List[dict]:
    if df is None or df.empty:
        return []
    df = df.copy()

    # Ensure common columns exist (so templates don’t break)
    for col in ["title", "company", "location", "url", "source", "score"]:
        if col not in df.columns:
            df[col] = ""

    return df.head(max_rows).to_dict(orient="records")


def _counts_by_source(jobs: List[Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for j in jobs:
        src = getattr(j, "source", "") or ""
        counts[src] = counts.get(src, 0) + 1
    return counts


# ---------------------------------------------------------
# Health & homepage
# ---------------------------------------------------------
@app.get("/health", response_class=JSONResponse)
def health():
    return {
        "status": "ok",
        "app": getattr(settings, "app_name", "Auto Apply"),
    }


@app.head("/", response_class=PlainTextResponse)
def head_root():
    # Render sometimes sends HEAD /; return 200 OK
    return PlainTextResponse("OK", status_code=200)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": getattr(settings, "app_name", "Auto Apply"),
            "ai_enabled": can_generate(),
        },
    )


# ---------------------------------------------------------
# Search + Match
# ---------------------------------------------------------
@app.post("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    cv_file: UploadFile,
    query: str = Form("engineer"),
    limit: int = Form(50),
):
    # Save uploaded CV
    file_id = uuid.uuid4().hex
    suffix = Path(cv_file.filename or "").suffix.lower() or ".txt"
    file_path = UPLOAD_DIR / f"{file_id}{suffix}"

    content = await cv_file.read()
    file_path.write_bytes(content)

    # Parse CV
    cv_text, cv_type = parse_cv(file_path)
    CV_STORE[file_id] = cv_text

    # Fetch multi-source jobs
    jobs, errors = fetch_all(query=query, limit=int(limit))
    counts = _counts_by_source(jobs)

    # Match + score
    df = match_jobs(cv_text, jobs)

    # Save CSV (for download & revisits)
    csv_path = DATA_DIR / f"{file_id}_jobs_scored.csv"
    df.to_csv(csv_path, index=False)

    rows = _df_to_rows(df, max_rows=100)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "app_name": getattr(settings, "app_name", "Auto Apply"),
            "query": query,
            "cv_type": cv_type,
            "total": int(len(df)) if df is not None else 0,
            "rows": rows,
            "file_id": file_id,
            "ai_enabled": can_generate(),
            "source_counts": counts,
            "source_errors": errors,
        },
    )


# ---------------------------------------------------------
# View previous results
# ---------------------------------------------------------
@app.get("/results/{file_id}", response_class=HTMLResponse)
def results(request: Request, file_id: str):
    csv_path = DATA_DIR / f"{file_id}_jobs_scored.csv"
    if not csv_path.exists():
        return HTMLResponse("Results not found.", status_code=404)

    df = pd.read_csv(csv_path)
    rows = _df_to_rows(df, max_rows=100)

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "app_name": getattr(settings, "app_name", "Auto Apply"),
            "query": "previous",
            "cv_type": "stored",
            "total": int(len(df)),
            "rows": rows,
            "file_id": file_id,
            "ai_enabled": can_generate(),
            "source_counts": {},
            "source_errors": [],
        },
    )


# ---------------------------------------------------------
# Download CSV
# ---------------------------------------------------------
@app.get("/download/{file_id}")
def download(file_id: str):
    csv_path = DATA_DIR / f"{file_id}_jobs_scored.csv"
    if not csv_path.exists():
        return HTMLResponse("CSV not found.", status_code=404)

    return FileResponse(
        path=str(csv_path),
        filename="jobs_scored.csv",
        media_type="text/csv",
    )


# ---------------------------------------------------------
# OpenAI cover letter
# ---------------------------------------------------------
@app.post("/cover-letter", response_class=HTMLResponse)
def cover_letter(
    request: Request,
    file_id: str = Form(...),
    row_index: int = Form(...),
):
    csv_path = DATA_DIR / f"{file_id}_jobs_scored.csv"
    if not csv_path.exists():
        return HTMLResponse("Results not found.", status_code=404)

    if not can_generate():
        return HTMLResponse("OPENAI_API_KEY not set. AI drafting disabled.", status_code=400)

    df = pd.read_csv(csv_path)
    if row_index < 0 or row_index >= len(df):
        return HTMLResponse("Invalid job row.", status_code=400)

    job_row = df.iloc[int(row_index)].to_dict()
    cv_text = CV_STORE.get(file_id, "")

    job_title = _safe_get(job_row, "title", "job_title", default="Job Role")
    company = _safe_get(job_row, "company", "company_name", default="Company")
    location = _safe_get(job_row, "location", "city", "region", default="Location")
    job_url = _safe_get(job_row, "url", "link", "apply_url", default="")
    description = _safe_get(job_row, "description", "job_description", default="")

    try:
        letter = generate_cover_letter(
            cv_text=cv_text,
            job_title=job_title,
            company=company,
            location=location,
            job_url=job_url,
            extra={"job_description": description},
        )
    except Exception as e:
        return HTMLResponse(f"Cover letter error: {e}", status_code=500)

    return templates.TemplateResponse(
        "cover_letter.html",
        {
            "request": request,
            "app_name": getattr(settings, "app_name", "Auto Apply"),
            "job": job_row,
            "letter": letter,
            "file_id": file_id,
        },
    )


# ---------------------------------------------------------
# Debug endpoint: see exactly what sources return
# ---------------------------------------------------------
@app.get("/debug/sources", response_class=JSONResponse)
def debug_sources(q: str = "engineer", limit: int = 20):
    jobs, errors = fetch_all(q, int(limit))
    return {
        "query": q,
        "limit": int(limit),
        "total_jobs": len(jobs),
        "counts_by_source": _counts_by_source(jobs),
        "errors": errors,
        "env": {
            "ADZUNA_APP_ID_set": bool(os.getenv("ADZUNA_APP_ID")),
            "ADZUNA_APP_KEY_set": bool(os.getenv("ADZUNA_APP_KEY")),
            "ADZUNA_COUNTRY": os.getenv("ADZUNA_COUNTRY", ""),
            "OPENAI_API_KEY_set": bool(os.getenv("OPENAI_API_KEY")),
            "OPENAI_MODEL": os.getenv("OPENAI_MODEL", ""),
            "GREENHOUSE_BOARDS": os.getenv("GREENHOUSE_BOARDS", ""),
            "LEVER_BOARDS": os.getenv("LEVER_BOARDS", ""),
        },
    }

=======
from fastapi import FastAPI
from app.routes import auth, users, jobs, cv, billing

app = FastAPI(title="Makwande Careers Pro")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(cv.router)
app.include_router(billing.router)

@app.get("/healthz")
def health():
    return {"ok": True, "service": "makwande-livecareer"}
>>>>>>> fdbc3e6 (Fix database connection for Render PostgreSQL)

from __future__ import annotations

from pathlib import Path
import uuid

import pandas as pd
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.services.cv_parse import parse_cv
from app.services.job_sources import fetch_all
from app.services.matching import match_jobs
from app.services.cover_letter import generate_cover_letter, can_generate


# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# App
app = FastAPI(title=settings.app_name)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# In-memory CV store (for MVP only)
CV_STORE: dict[str, str] = {}


# Home page
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": settings.app_name,
        },
    )


# Search + match
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

    # Fetch jobs
    jobs, errors = fetch_all(query=query, limit=int(limit))
    print("JOB FETCH ERRORS:", errors)

    # Match
    df = match_jobs(cv_text, jobs)

    # Save CSV
    csv_path = DATA_DIR / f"{file_id}_jobs_scored.csv"
    df.to_csv(csv_path, index=False)

    rows = df.head(100).to_dict(orient="records") if not df.empty else []

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "query": query,
            "cv_type": cv_type,
            "total": int(len(df)),
            "rows": rows,
            "file_id": file_id,
        },
    )


# View previous results
@app.get("/results/{file_id}", response_class=HTMLResponse)
def results(request: Request, file_id: str):
    csv_path = DATA_DIR / f"{file_id}_jobs_scored.csv"

    if not csv_path.exists():
        return HTMLResponse("Results not found.", status_code=404)

    df = pd.read_csv(csv_path)
    rows = df.head(100).to_dict(orient="records") if not df.empty else []

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "query": "previous",
            "cv_type": "stored",
            "total": int(len(df)),
            "rows": rows,
            "file_id": file_id,
        },
    )


# Download CSV
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


# Generate cover letter
@app.post("/cover-letter", response_class=HTMLResponse)
def cover_letter(
    request: Request,
    file_id: str = Form(...),
    row_index: int = Form(...),
):
    csv_path = DATA_DIR / f"{file_id}_jobs_scored.csv"

    if not csv_path.exists():
        return HTMLResponse("Results not found.", status_code=404)

    df = pd.read_csv(csv_path)

    if row_index < 0 or row_index >= len(df):
        return HTMLResponse("Invalid row.", status_code=400)

    job = df.iloc[int(row_index)].to_dict()
    cv_text = CV_STORE.get(file_id, "")

    if not can_generate():
        return HTMLResponse(
            "OPENAI_API_KEY not set. AI drafting disabled.",
            status_code=400,
        )

    try:
        letter = generate_cover_letter(cv_text=cv_text, job=job)
    except Exception as e:
        return HTMLResponse(f"Error: {e}", status_code=500)

    return templates.TemplateResponse(
        "cover_letter.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "job": job,
            "letter": letter,
            "file_id": file_id,
        },
    )

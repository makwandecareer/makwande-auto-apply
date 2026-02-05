import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from fastapi import Depends

from app.core.auth_utils import get_current_user
from app.services.cv_text import extract_cv_text
from app.services.revamp_engine import revamp_cv
from app.services.cover_letter_engine import generate_cover_letter
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends   # ✅ ADD THIS
)


router = APIRouter(prefix="/cv", tags=["CV"])

UPLOAD_DIR = os.path.join("data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

fetch(`${getApiBase()}/api/auth/login`)

class RevampRequest(BaseModel):
    stored_as: str | None = None
    target_role: str | None = ""
    country: str | None = "South Africa"
    cv_text: str | None = None


class CoverLetterRequest(BaseModel):
    stored_as: str | None = None
    cv_text: str | None = None
    job_title: str
    company: str
    job_description: str | None = ""


@router.post("/upload")
async def upload(file: UploadFile = File(...), user=Depends(get_current_user)):  # noqa: F821
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided")

    allowed = (".pdf", ".docx", ".doc")
    if not file.filename.lower().endswith(allowed):
        raise HTTPException(status_code=400, detail="Upload PDF or DOCX only")

    ext = os.path.splitext(file.filename)[1].lower()
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    with open(saved_path, "wb") as f:
        f.write(content)

    cv_text = extract_cv_text(saved_path)

    return {
        "message": "CV uploaded ✅",
        "filename": file.filename,
        "stored_as": saved_name,
        "path": saved_path,
        "text_preview": cv_text[:600] if cv_text else "",
        "user": user,
    }


@router.post("/revamp")
def revamp(req: RevampRequest, user=Depends(get_current_user)):  # noqa: F821
    # You can pass raw cv_text OR a stored file reference
    cv_text = (req.cv_text or "").strip()

    if not cv_text and req.stored_as:
        p = os.path.join(UPLOAD_DIR, req.stored_as)
        if not os.path.exists(p):
            raise HTTPException(status_code=404, detail="Stored CV not found")
        cv_text = extract_cv_text(p)

    if not cv_text:
        raise HTTPException(status_code=400, detail="No CV text provided or extractable")

    res = revamp_cv(cv_text=cv_text, target_role=req.target_role or "", country=req.country or "South Africa")
    if not res["ok"]:
        raise HTTPException(status_code=500, detail=res.get("error", "Revamp failed"))

    return {"ok": True, "user": user, "revamp": res["result"]}


@router.post("/cover-letter")
def cover_letter(req: CoverLetterRequest, user=Depends(get_current_user)):  # noqa: F821
    cv_text = (req.cv_text or "").strip()

    if not cv_text and req.stored_as:
        p = os.path.join(UPLOAD_DIR, req.stored_as)
        if not os.path.exists(p):
            raise HTTPException(status_code=404, detail="Stored CV not found")
        cv_text = extract_cv_text(p)

    if not cv_text:
        raise HTTPException(status_code=400, detail="No CV text provided or extractable")

    res = generate_cover_letter(
        cv_text=cv_text,
        job_title=req.job_title,
        company=req.company,
        job_description=req.job_description or "",
    )

    if not res["ok"]:
        raise HTTPException(status_code=500, detail=res.get("error", "Cover letter failed"))

    return {"ok": True, "user": user, "cover_letter": res["result"]}

import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends   # ✅ ADD
from pydantic import BaseModel
from fastapi import Depends

from app.core.auth_utils import get_current_user
from app.services.storage_json import read_json, write_json

router = APIRouter(prefix="/jobs", tags=["Jobs"])

APPS_FILE = os.path.join("data", "applications.json")



class ApplyRequest(BaseModel):
    job_id: str
    job_title: str
    company: str
    location: str | None = ""
    job_url: str | None = ""
    notes: str | None = ""
    status: str | None = "Draft"  # Draft, Applied, Interview, Offer, Rejected


class UpdateStatusRequest(BaseModel):
    application_id: str
    status: str


@router.get("/search")
def search(q: str = "", country: str = "South Africa"):
    """
    Keep it simple: you can plug real sources later.
    For now it returns a placeholder response so frontend doesn't break.
    """
    return {
        "ok": True,
        "query": q,
        "country": country,
        "jobs": [],
        "message": "Connect real job sources later (API/DB).",
    }


@router.post("/apply")
def apply_job(req: ApplyRequest, user=Depends(get_current_user)):  # noqa: F821
    apps = read_json(APPS_FILE, [])

    new_id = f"APP-{len(apps)+1:06d}"
    record = {
        "application_id": new_id,
        "user_email": user["email"],
        "job_id": req.job_id,
        "job_title": req.job_title,
        "company": req.company,
        "location": req.location or "",
        "job_url": req.job_url or "",
        "notes": req.notes or "",
        "status": req.status or "Draft",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    apps.append(record)
    write_json(APPS_FILE, apps)

    return {"ok": True, "application": record}


@router.get("/applications")
def list_applications(user=Depends(get_current_user)):  # noqa: F821
    apps = read_json(APPS_FILE, [])
    mine = [a for a in apps if a.get("user_email") == user["email"]]
    return {"ok": True, "applications": mine}


@router.post("/applications/status")
def update_application_status(req: UpdateStatusRequest, user=Depends(get_current_user)):  # noqa: F821
    apps = read_json(APPS_FILE, [])

    found = None
    for a in apps:
        if a.get("application_id") == req.application_id and a.get("user_email") == user["email"]:
            a["status"] = req.status
            a["updated_at"] = datetime.utcnow().isoformat()
            found = a
            break

    if not found:
        raise HTTPException(status_code=404, detail="Application not found")

    write_json(APPS_FILE, apps)
    return {"ok": True, "application": found}

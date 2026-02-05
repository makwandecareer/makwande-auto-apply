import os
import json
import uuid
import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from db import get_db, utc_now_iso

# You already have auth; this function should return current user dict with email.
# Replace import below with your real auth dependency.
# Example: from auth import get_current_user
def get_current_user():
    raise RuntimeError("Wire your real get_current_user dependency here.")

router = APIRouter()

# =========================
# Models
# =========================

class DocumentCreate(BaseModel):
    doc_type: str = Field(..., pattern="^(cv|cover_letter)$")
    title: Optional[str] = None
    stored_as: Optional[str] = None
    content: Optional[str] = None
    meta: Optional[dict] = None

class SavedJobCreate(BaseModel):
    job_id: Optional[str] = None
    job_title: str
    company: Optional[str] = None
    location: Optional[str] = None
    job_url: Optional[str] = None
    match_score: Optional[float] = None

class RulesUpsert(BaseModel):
    countries: List[str] = []
    job_titles: List[str] = []
    keywords: List[str] = []
    blacklist_companies: List[str] = []
    min_match_score: float = 70.0

class PaystackInitRequest(BaseModel):
    plan_code: str = "PRO_MONTHLY"   # internal plan key
    amount_kobo: int = 30000         # R300 => 30000 kobo
    currency: str = "ZAR"

class PaystackVerifyRequest(BaseModel):
    reference: str

# =========================
# Documents
# =========================

@router.get("/docs")
def list_documents(user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM documents WHERE user_email=? ORDER BY created_at DESC",
            (user["email"],)
        ).fetchall()
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "doc_type": r["doc_type"],
            "title": r["title"],
            "stored_as": r["stored_as"],
            "created_at": r["created_at"],
            "meta": json.loads(r["meta_json"]) if r["meta_json"] else None
        })
    return out

@router.post("/docs")
def create_document(payload: DocumentCreate, user=Depends(get_current_user)):
    doc_id = str(uuid.uuid4())
    meta_json = json.dumps(payload.meta) if payload.meta else None
    with get_db() as db:
        db.execute("""
            INSERT INTO documents (id, user_email, doc_type, title, stored_as, content, meta_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, user["email"], payload.doc_type, payload.title, payload.stored_as, payload.content, meta_json, utc_now_iso()))
    return {"id": doc_id, "status": "created"}

# =========================
# Saved Jobs
# =========================

@router.get("/saved-jobs")
def list_saved_jobs(user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM saved_jobs WHERE user_email=? ORDER BY created_at DESC",
            (user["email"],)
        ).fetchall()
    return [dict(r) for r in rows]

@router.post("/saved-jobs")
def save_job(payload: SavedJobCreate, user=Depends(get_current_user)):
    item_id = str(uuid.uuid4())
    with get_db() as db:
        db.execute("""
            INSERT INTO saved_jobs (id, user_email, job_id, job_title, company, location, job_url, match_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_id, user["email"], payload.job_id, payload.job_title, payload.company, payload.location, payload.job_url, payload.match_score, utc_now_iso()))
    return {"id": item_id, "status": "saved"}

@router.delete("/saved-jobs/{saved_id}")
def delete_saved_job(saved_id: str, user=Depends(get_current_user)):
    with get_db() as db:
        cur = db.execute("DELETE FROM saved_jobs WHERE id=? AND user_email=?", (saved_id, user["email"]))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not found")
    return {"status": "deleted"}

# =========================
# Auto Apply Runs + Items
# =========================

@router.get("/autoapply/runs")
def list_runs(user=Depends(get_current_user)):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM autoapply_runs WHERE user_email=? ORDER BY started_at DESC LIMIT 50",
            (user["email"],)
        ).fetchall()
    return [dict(r) for r in rows]

@router.get("/autoapply/runs/{run_id}")
def get_run(run_id: str, user=Depends(get_current_user)):
    with get_db() as db:
        run = db.execute("SELECT * FROM autoapply_runs WHERE id=? AND user_email=?", (run_id, user["email"])).fetchone()
        if not run:
            raise HTTPException(404, "Run not found")
        items = db.execute("SELECT * FROM autoapply_run_items WHERE run_id=? AND user_email=? ORDER BY created_at DESC",
                           (run_id, user["email"])).fetchall()
    return {"run": dict(run), "items": [dict(i) for i in items]}

# Helpers you can call from your /jobs/apply logic:
def start_run(db, user_email: str, mode: str = "manual") -> str:
    run_id = str(uuid.uuid4())
    db.execute("""
        INSERT INTO autoapply_runs (id, user_email, mode, status, total, success, failed, started_at)
        VALUES (?, ?, ?, 'running', 0, 0, 0, ?)
    """, (run_id, user_email, mode, utc_now_iso()))
    return run_id

def add_run_item(db, run_id: str, user_email: str, job: dict, result: str, error: str = None):
    item_id = str(uuid.uuid4())
    db.execute("""
        INSERT INTO autoapply_run_items
        (id, run_id, user_email, job_id, job_title, company, location, job_url, result, error, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item_id, run_id, user_email,
        job.get("job_id"), job.get("job_title"), job.get("company"), job.get("location"), job.get("job_url"),
        result, error, utc_now_iso()
    ))

def finish_run(db, run_id: str, user_email: str, total: int, success: int, failed: int, status: str = "complete"):
    db.execute("""
        UPDATE autoapply_runs
        SET status=?, total=?, success=?, failed=?, finished_at=?
        WHERE id=? AND user_email=?
    """, (status, total, success, failed, utc_now_iso(), run_id, user_email))

# =========================
# Auto Apply Rules
# =========================

@router.get("/autoapply/rules")
def get_rules(user=Depends(get_current_user)):
    with get_db() as db:
        r = db.execute("SELECT * FROM autoapply_rules WHERE user_email=?", (user["email"],)).fetchone()

    if not r:
        return {
            "countries": ["South Africa"],
            "job_titles": [],
            "keywords": [],
            "blacklist_companies": [],
            "min_match_score": 70.0
        }

    def split_csv(s): return [x.strip() for x in (s or "").split(",") if x.strip()]

    return {
        "countries": split_csv(r["countries_csv"]),
        "job_titles": split_csv(r["job_titles_csv"]),
        "keywords": split_csv(r["keywords_csv"]),
        "blacklist_companies": split_csv(r["blacklist_companies_csv"]),
        "min_match_score": float(r["min_match_score"] or 70.0)
    }

@router.post("/autoapply/rules")
def upsert_rules(payload: RulesUpsert, user=Depends(get_current_user)):
    def to_csv(arr): return ",".join([x.strip() for x in arr if x and x.strip()])

    with get_db() as db:
        db.execute("""
            INSERT INTO autoapply_rules (user_email, countries_csv, job_titles_csv, keywords_csv, blacklist_companies_csv, min_match_score, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_email) DO UPDATE SET
              countries_csv=excluded.countries_csv,
              job_titles_csv=excluded.job_titles_csv,
              keywords_csv=excluded.keywords_csv,
              blacklist_companies_csv=excluded.blacklist_companies_csv,
              min_match_score=excluded.min_match_score,
              updated_at=excluded.updated_at
        """, (
            user["email"],
            to_csv(payload.countries),
            to_csv(payload.job_titles),
            to_csv(payload.keywords),
            to_csv(payload.blacklist_companies),
            float(payload.min_match_score),
            utc_now_iso()
        ))
    return {"status": "saved"}

# =========================
# Subscription + Paystack
# =========================

@router.get("/billing/subscription")
def get_subscription(user=Depends(get_current_user)):
    with get_db() as db:
        row = db.execute("SELECT * FROM subscriptions WHERE user_email=?", (user["email"],)).fetchone()
    if not row:
        return {"status": "inactive", "plan_code": None}
    return dict(row)

@router.post("/billing/paystack/init")
def paystack_init(payload: PaystackInitRequest, user=Depends(get_current_user)):
    secret = os.getenv("PAYSTACK_SECRET_KEY")
    app_url = os.getenv("APP_URL", "").rstrip("/")
    if not secret:
        raise HTTPException(500, "PAYSTACK_SECRET_KEY not set")
    if not app_url:
        raise HTTPException(500, "APP_URL not set")

    reference = f"mk_{uuid.uuid4().hex}"
    with get_db() as db:
        db.execute("""
            INSERT INTO payments (reference, user_email, amount_kobo, currency, status, gateway_response, created_at)
            VALUES (?, ?, ?, ?, 'initiated', NULL, ?)
        """, (reference, user["email"], payload.amount_kobo, payload.currency, utc_now_iso()))

    resp = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
        json={
            "email": user["email"],
            "amount": payload.amount_kobo,
            "currency": payload.currency,
            "reference": reference,
            "callback_url": f"{app_url}/subscription.html?ref={reference}"
        },
        timeout=25
    )
    data = resp.json()
    if not data.get("status"):
        raise HTTPException(400, data.get("message", "Paystack init failed"))
    return {
        "reference": reference,
        "authorization_url": data["data"]["authorization_url"],
        "access_code": data["data"]["access_code"]
    }

@router.post("/billing/paystack/verify")
def paystack_verify(payload: PaystackVerifyRequest, user=Depends(get_current_user)):
    secret = os.getenv("PAYSTACK_SECRET_KEY")
    if not secret:
        raise HTTPException(500, "PAYSTACK_SECRET_KEY not set")

    resp = requests.get(
        f"https://api.paystack.co/transaction/verify/{payload.reference}",
        headers={"Authorization": f"Bearer {secret}"},
        timeout=25
    )
    data = resp.json()
    if not data.get("status"):
        raise HTTPException(400, data.get("message", "Verify failed"))

    tx = data["data"]
    status = tx.get("status")  # "success"
    amount = int(tx.get("amount") or 0)
    currency = tx.get("currency") or "ZAR"
    gateway_resp = tx.get("gateway_response") or ""

    with get_db() as db:
        db.execute("""
            UPDATE payments
            SET status=?, gateway_response=?
            WHERE reference=? AND user_email=?
        """, ("success" if status == "success" else "failed", gateway_resp, payload.reference, user["email"]))

        # Activate subscription on success
        if status == "success":
            db.execute("""
                INSERT INTO subscriptions (user_email, plan_code, status, updated_at)
                VALUES (?, 'PRO_MONTHLY', 'active', ?)
                ON CONFLICT(user_email) DO UPDATE SET
                  plan_code='PRO_MONTHLY', status='active', updated_at=excluded.updated_at
            """, (user["email"], utc_now_iso()))

    return {
        "ok": True,
        "status": status,
        "amount_kobo": amount,
        "currency": currency,
        "gateway_response": gateway_resp
    }

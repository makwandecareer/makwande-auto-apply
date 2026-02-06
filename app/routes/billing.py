# app/routes/billing.py
import os
import json
import hmac
import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/billing", tags=["Billing (Paystack)"])

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
PAYSTACK_PUBLIC_KEY = os.getenv("PAYSTACK_PUBLIC_KEY", "")
PAYSTACK_BASE_URL = os.getenv("PAYSTACK_BASE_URL", "https://api.paystack.co")

DB_PATH = os.getenv("SQLITE_DB_PATH", "data/app.db")


# -----------------------------
# DB helpers (no SQLAlchemy)
# -----------------------------
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True) if os.path.dirname(DB_PATH) else None
    return sqlite3.connect(DB_PATH)

def _init_db():
    with _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            amount_kobo INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'ZAR',
            status TEXT NOT NULL DEFAULT 'initialized',
            channel TEXT,
            paid_at TEXT,
            plan_code TEXT,
            metadata_json TEXT,
            raw_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        conn.commit()

def _upsert_payment(reference: str, email: str, amount_kobo: int, currency: str = "ZAR",
                    status: str = "initialized", plan_code: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    raw: Optional[Dict[str, Any]] = None,
                    channel: Optional[str] = None,
                    paid_at: Optional[str] = None):
    _init_db()
    now = _utc_now_iso()
    metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
    raw_json = json.dumps(raw or {}, ensure_ascii=False)

    with _connect() as conn:
        conn.execute("""
        INSERT INTO payments (reference, email, amount_kobo, currency, status, channel, paid_at, plan_code,
                             metadata_json, raw_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(reference) DO UPDATE SET
            email=excluded.email,
            amount_kobo=excluded.amount_kobo,
            currency=excluded.currency,
            status=excluded.status,
            channel=COALESCE(excluded.channel, payments.channel),
            paid_at=COALESCE(excluded.paid_at, payments.paid_at),
            plan_code=COALESCE(excluded.plan_code, payments.plan_code),
            metadata_json=excluded.metadata_json,
            raw_json=excluded.raw_json,
            updated_at=excluded.updated_at;
        """, (reference, email, amount_kobo, currency, status, channel, paid_at, plan_code,
              metadata_json, raw_json, now, now))
        conn.commit()

def _get_payment(reference: str) -> Optional[Dict[str, Any]]:
    _init_db()
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM payments WHERE reference = ?", (reference,)).fetchone()
        return dict(row) if row else None


# -----------------------------
# Schemas
# -----------------------------
class PaystackInitRequest(BaseModel):
    email: EmailStr
    amount: int = Field(..., description="Amount in ZAR rands (e.g. 300 means R300)")
    currency: str = Field(default="ZAR")
    callback_url: Optional[str] = Field(default=None, description="Where Paystack should redirect after payment")
    plan_code: Optional[str] = Field(default=None, description="Optional Paystack plan code for subscriptions")
    metadata: Optional[Dict[str, Any]] = Field(default=None)

class PaystackInitResponse(BaseModel):
    reference: str
    authorization_url: str
    access_code: str

class VerifyResponse(BaseModel):
    reference: str
    status: str
    paid: bool
    amount: int
    currency: str
    email: str
    paid_at: Optional[str] = None


# -----------------------------
# Utilities
# -----------------------------
def _require_secret_key():
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="PAYSTACK_SECRET_KEY is not set")

def _headers():
    return {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

def _rands_to_kobo(amount_rands: int) -> int:
    # Paystack expects amount in the smallest unit (kobo/cents)
    # For ZAR, treat as cents -> multiply by 100
    if amount_rands <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    return amount_rands * 100

def _paystack_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    _require_secret_key()
    url = f"{PAYSTACK_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    resp = requests.post(url, headers=_headers(), json=payload, timeout=30)
    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Paystack returned non-JSON response")
    if not resp.ok or not data.get("status"):
        # Paystack errors often appear in message
        raise HTTPException(status_code=502, detail=f"Paystack error: {data.get('message', 'unknown')}")
    return data

def _paystack_get(path: str) -> Dict[str, Any]:
    _require_secret_key()
    url = f"{PAYSTACK_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    resp = requests.get(url, headers=_headers(), timeout=30)
    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Paystack returned non-JSON response")
    if not resp.ok or not data.get("status"):
        raise HTTPException(status_code=502, detail=f"Paystack error: {data.get('message', 'unknown')}")
    return data

def _verify_webhook_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    if not signature or not PAYSTACK_SECRET_KEY:
        return False
    computed = hmac.new(
        PAYSTACK_SECRET_KEY.encode("utf-8"),
        raw_body,
        hashlib.sha512
    ).hexdigest()
    # Use hmac.compare_digest to avoid timing attacks
    return hmac.compare_digest(computed, signature)


# -----------------------------
# Routes
# -----------------------------
@router.get("/paystack/config")
def paystack_config():
    """
    Expose ONLY the Paystack public key to the frontend (safe).
    """
    return {
        "provider": "paystack",
        "public_key": PAYSTACK_PUBLIC_KEY,
        "currency_default": "ZAR",
    }


@router.post("/paystack/init", response_model=PaystackInitResponse)
def init_payment(req: PaystackInitRequest):
    """
    Start a Paystack transaction and return an authorization_url.
    """
    amount_kobo = _rands_to_kobo(req.amount)

    payload: Dict[str, Any] = {
        "email": req.email,
        "amount": amount_kobo,
        "currency": req.currency or "ZAR",
    }
    if req.callback_url:
        payload["callback_url"] = req.callback_url
    if req.metadata:
        payload["metadata"] = req.metadata
    if req.plan_code:
        payload["plan"] = req.plan_code

    data = _paystack_post("/transaction/initialize", payload)
    d = data["data"]

    reference = d["reference"]
    _upsert_payment(
        reference=reference,
        email=req.email,
        amount_kobo=amount_kobo,
        currency=req.currency or "ZAR",
        status="initialized",
        plan_code=req.plan_code,
        metadata=req.metadata,
        raw=data,
    )

    return PaystackInitResponse(
        reference=reference,
        authorization_url=d["authorization_url"],
        access_code=d["access_code"],
    )


@router.get("/paystack/verify/{reference}", response_model=VerifyResponse)
def verify_payment(reference: str):
    """
    Verify a Paystack transaction by reference.
    """
    data = _paystack_get(f"/transaction/verify/{reference}")
    d = data["data"]

    status = (d.get("status") or "").lower()
    paid = status == "success"

    email = (d.get("customer") or {}).get("email") or ""
    amount_kobo = int(d.get("amount") or 0)
    currency = d.get("currency") or "ZAR"
    paid_at = d.get("paid_at")

    _upsert_payment(
        reference=reference,
        email=email or (_get_payment(reference) or {}).get("email", "unknown@example.com"),
        amount_kobo=amount_kobo,
        currency=currency,
        status="success" if paid else status or "failed",
        channel=d.get("channel"),
        paid_at=paid_at,
        metadata=d.get("metadata") or {},
        raw=data,
    )

    return VerifyResponse(
        reference=reference,
        status="success" if paid else (status or "failed"),
        paid=paid,
        amount=amount_kobo // 100,  # back to rands for UI convenience
        currency=currency,
        email=email,
        paid_at=paid_at,
    )


@router.post("/paystack/webhook")
async def paystack_webhook(request: Request):
    """
    Paystack webhook endpoint.

    ✅ Verifies x-paystack-signature using HMAC SHA512.
    ✅ Updates SQLite payment status.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not _verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid Paystack signature")

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("event")
    data = event.get("data") or {}

    # Most important fields
    reference = data.get("reference")
    status = (data.get("status") or "").lower()
    email = (data.get("customer") or {}).get("email") or ""
    amount_kobo = int(data.get("amount") or 0)
    currency = data.get("currency") or "ZAR"
    paid_at = data.get("paid_at")
    channel = data.get("channel")

    if reference:
        # Map webhook events to a clean status
        normalized_status = "success" if status == "success" else (status or "unknown")

        _upsert_payment(
            reference=reference,
            email=email or (_get_payment(reference) or {}).get("email", "unknown@example.com"),
            amount_kobo=amount_kobo or int((_get_payment(reference) or {}).get("amount_kobo", 0) or 0),
            currency=currency,
            status=normalized_status,
            channel=channel,
            paid_at=paid_at,
            metadata=data.get("metadata") or {},
            raw=event,
        )

    # Always return 200 so Paystack considers it received
    return {"received": True, "event": event_type}

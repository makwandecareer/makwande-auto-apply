# app/routes/users.py

import os
import json
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/users", tags=["users"])

# Use /tmp by default on Render (writable)
DATA_DIR = os.getenv("DATA_DIR", "/tmp")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")


def _ensure_users_file() -> None:
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _load_users() -> List[Dict[str, Any]]:
    _ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        # If corrupted, reset
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []
    except Exception:
        return []


def _safe_user(user: Dict[str, Any]) -> Dict[str, Any]:
    safe = dict(user)
    safe.pop("password_hash", None)
    safe.pop("hashed_password", None)
    safe.pop("password", None)
    return safe


@router.get("/me")
def me(email: str = Query(..., description="For now, pass email as query param e.g. /me?email=test@x.com")):
    """
    TEMPORARY (Auth disabled):
    Return user details by email without JWT.
    We'll lock this down later with get_current_user.
    """
    users = _load_users()
    user = next((u for u in users if (u.get("email") or "").lower() == email.lower()), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _safe_user(user)


@router.get("/by-email")
def get_user_by_email(email: str = Query(...)):
    """
    TEMPORARY (Auth disabled):
    Return user details by email without JWT.
    """
    users = _load_users()
    user = next((u for u in users if (u.get("email") or "").lower() == email.lower()), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _safe_user(user)

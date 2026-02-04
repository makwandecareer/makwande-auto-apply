# app/routes/auth.py
import os
import json
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

USERS_FILE = os.path.join("app", "data", "users.json")


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


def _load_users() -> List[Dict[str, Any]]:
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_users(users: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


@router.get("/ping")
def ping():
    return {"ok": True, "message": "auth up"}


@router.post("/signup")
def signup(payload: SignupRequest):
    users = _load_users()
    email = payload.email.lower().strip()

    if any(u.get("email") == email for u in users):
        raise HTTPException(status_code=409, detail="User already exists")

    if not payload.password or len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = {
        "email": email,
        "full_name": payload.full_name or "",
        "password_hash": hash_password(payload.password),
    }
    users.append(user)
    _save_users(users)

    return {"ok": True, "message": "Signup successful"}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    IMPORTANT:
    Swagger Authorize sends form fields:
      - username
      - password
    So we accept OAuth2PasswordRequestForm here.
    We'll treat username as email.
    """
    users = _load_users()
    email = (form_data.username or "").lower().strip()
    password = form_data.password or ""

    user = next((u for u in users if u.get("email") == email), None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(token: str = Depends(lambda: None)):
    # If you already have /api/auth/me working elsewhere, keep it.
    # Otherwise, tell me and I'll align it with your existing users.py dependency.
    return {"note": "Use your existing /api/auth/me dependency logic (token decoding + user lookup)."}


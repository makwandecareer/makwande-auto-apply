import os
import json
from datetime import timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ----------------------------
# Storage (simple JSON DB)
# ----------------------------
DATA_DIR = os.getenv("DATA_DIR", "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def _load_users() -> Dict[str, Any]:
    _ensure_data_dir()
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        # If file is corrupted, fail safely
        return {}

def _save_users(users: Dict[str, Any]) -> None:
    _ensure_data_dir()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

# ----------------------------
# Schemas
# ----------------------------
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)  # no max here because bcrypt_sha256 supports long inputs
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ----------------------------
# Routes
# ----------------------------
@router.get("/ping")
def ping():
    return {"status": "ok", "message": "auth router alive ✅"}

@router.post("/signup")
def signup(payload: SignupRequest):
    try:
        email = payload.email.strip().lower()
        password = payload.password  # IMPORTANT: hash only this string

        users = _load_users()
        if email in users:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(password)

        users[email] = {
            "email": email,
            "full_name": payload.full_name or "",
            "password_hash": hashed_password,
        }
        _save_users(users)

        return {"message": "Signup successful ✅", "email": email, "full_name": users[email]["full_name"]}

    except HTTPException:
        raise
    except Exception as e:
        # Keep this clean but informative
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    try:
        email = payload.email.strip().lower()
        users = _load_users()

        user = users.get(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if not verify_password(payload.password, user.get("password_hash", "")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token = create_access_token(
            data={"sub": email},
            expires_delta=timedelta(days=30)
        )
        return {"access_token": token, "token_type": "bearer"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return {"user": current_user}

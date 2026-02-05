# app/routes/users.py

import os
import json
from typing import Dict, Any, List

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

router = APIRouter(prefix="/api/users", tags=["users"])

# On Render, write to /tmp unless you mounted a Disk and set DATA_DIR to that path.
DATA_DIR = os.getenv("DATA_DIR", "/tmp")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, "users.json")

SECRET_KEY = os.getenv("SECRET_KEY", "makwande-secret-key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _ensure_users_file() -> None:
    try:
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User storage error: {str(e)}")


def _load_users() -> List[Dict[str, Any]]:
    _ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        # reset corrupted file safely
        try:
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception:
            pass
        return []
    except Exception:
        return []


def _decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    payload = _decode_token(token)

    email = payload.get("sub") or payload.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Token missing user identity (email/sub)")

    users = _load_users()
    user = next((u for u in users if (u.get("email") or "").lower() == email.lower()), None)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Never expose password hashes
    safe_user = dict(user)
    safe_user.pop("password_hash", None)
    safe_user.pop("hashed_password", None)
    safe_user.pop("password", None)

    return safe_user


@router.get("/me", operation_id="users_me")
def me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user


@router.get("/{email}", operation_id="users_get_by_email")
def get_user_by_email(email: str, current_user: Dict[str, Any] = Depends(get_current_user)):
    users = _load_users()
    user = next((u for u in users if (u.get("email") or "").lower() == email.lower()), None)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    safe_user = dict(user)
    safe_user.pop("password_hash", None)
    safe_user.pop("hashed_password", None)
    safe_user.pop("password", None)

    return safe_user
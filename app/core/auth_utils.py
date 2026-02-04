# app/core/auth_utils.py

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import jwt  # pyjwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# ----------------------------
# Config
# ----------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "makwande-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# IMPORTANT: this tokenUrl MUST match your login endpoint exactly
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Store users in a JSON file (simple + works on Render disk)
USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "users.json")
USERS_FILE = os.path.abspath(USERS_FILE)


# ----------------------------
# Helpers: file storage
# ----------------------------
def _ensure_users_file() -> None:
    folder = os.path.dirname(USERS_FILE)
    os.makedirs(folder, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def load_users() -> List[Dict[str, Any]]:
    _ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except Exception:
        return []


def save_users(users: List[Dict[str, Any]]) -> None:
    _ensure_users_file()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    email_l = (email or "").strip().lower()
    for u in load_users():
        if (u.get("email") or "").strip().lower() == email_l:
            return u
    return None


# ----------------------------
# Password rules (bcrypt limit)
# ----------------------------
def validate_password_length(password: str) -> None:
    """
    bcrypt has a hard input limit of 72 bytes. If longer, hashing will truncate silently,
    which is unsafe/confusing. We block it explicitly.
    """
    if password is None:
        raise HTTPException(status_code=400, detail="Password is required")

    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be longer than 72 bytes. Please use a shorter password.",
        )


def hash_password(password: str) -> str:
    validate_password_length(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # validate length before verify too (consistent behavior)
    validate_password_length(plain_password)
    return pwd_context.verify(plain_password, hashed_password)


# ----------------------------
# JWT helpers
# ----------------------------
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = dict(data)

    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ----------------------------
# FastAPI dependency
# ----------------------------
def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    payload = decode_token(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # never return hashed password outwards (routes can re-shape response)
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return safe_user

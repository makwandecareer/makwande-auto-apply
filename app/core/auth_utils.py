import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt  # pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext


# =========================
# Config
# =========================
SECRET_KEY = os.getenv("SECRET_KEY", "makwande-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# IMPORTANT: tokenUrl must match your login endpoint path for Swagger Authorize
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Store users in JSON file (works on Render disk too)
USERS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "users.json"))


# =========================
# Models
# =========================
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserPublic(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True


# =========================
# Storage helpers
# =========================
def _ensure_users_file() -> None:
    folder = os.path.dirname(USERS_FILE)
    os.makedirs(folder, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _load_users() -> list[dict]:
    _ensure_users_file()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []


def _save_users(users: list[dict]) -> None:
    _ensure_users_file()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def get_user_by_email(email: str) -> Optional[dict]:
    users = _load_users()
    for u in users:
        if (u.get("email") or "").lower() == email.lower():
            return u
    return None


# =========================
# Password + JWT helpers
# =========================
def hash_password(password: str) -> str:
    # bcrypt has a 72-byte limit; enforce it safely
    pw = password.encode("utf-8")
    if len(pw) > 72:
        raise HTTPException(status_code=400, detail="Password too long (max 72 bytes).")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# =========================
# Core actions
# =========================
def signup_user(req: SignupRequest) -> UserPublic:
    users = _load_users()

    if get_user_by_email(req.email):
        raise HTTPException(status_code=409, detail="User already exists")

    new_user = {
        "email": req.email,
        "full_name": req.full_name,
        "password_hash": hash_password(req.password),
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }

    users.append(new_user)
    _save_users(users)

    return UserPublic(email=req.email, full_name=req.full_name, is_active=True)


def authenticate_user(email: str, password: str) -> dict:
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User is disabled")

    if not verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user


# =========================
# Dependency for protected routes
# =========================
def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="User disabled")

    return user

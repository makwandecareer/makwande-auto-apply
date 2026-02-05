import os
import json
import time
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

logger = logging.getLogger("makwande-auto-apply")

# -------------------------
# Config
# -------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "makwande-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

# Swagger Authorize uses this tokenUrl
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ✅ IMPORTANT: avoids bcrypt 72-byte limitation
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

USERS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "users.json"))
LOCK_FILE = USERS_FILE + ".lock"


# -------------------------
# File helpers (safe JSON)
# -------------------------
def _ensure_users_file() -> None:
    folder = os.path.dirname(USERS_FILE)
    os.makedirs(folder, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _acquire_lock(timeout_sec: float = 5.0, poll_sec: float = 0.05) -> None:
    start = time.time()
    while True:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return
        except FileExistsError:
            if time.time() - start > timeout_sec:
                raise RuntimeError("Could not acquire users.json lock (timeout).")
            time.sleep(poll_sec)


def _release_lock() -> None:
    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass


def _read_users() -> List[Dict[str, Any]]:
    _ensure_users_file()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        raw = f.read().strip()
        if not raw:
            return []
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception:
            logger.exception("users.json is corrupted — resetting to []")
            return []


def _atomic_write_users(users: List[Dict[str, Any]]) -> None:
    _ensure_users_file()
    tmp_path = USERS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, USERS_FILE)


def _write_users(users: List[Dict[str, Any]]) -> None:
    _acquire_lock()
    try:
        _atomic_write_users(users)
    finally:
        _release_lock()


# -------------------------
# Password helpers
# -------------------------
def get_password_hash(password: str) -> str:
    if not isinstance(password, str) or not password.strip():
        raise HTTPException(status_code=422, detail="Password is required.")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        logger.exception("Password verify failed")
        return False


# -------------------------
# User helpers
# -------------------------
def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    users = _read_users()
    for u in users:
        if u.get("email", "").lower() == str(email).lower():
            return u
    return None


def create_user(email: str, password: str, full_name: str = "") -> Dict[str, Any]:
    email = str(email).strip().lower()

    if get_user_by_email(email):
        raise HTTPException(status_code=409, detail="User already exists")

    users = _read_users()

    user = {
        "email": email,
        "full_name": full_name or "",
        "is_active": True,
        "password_hash": get_password_hash(password),
        "created_at": datetime.utcnow().isoformat(),
    }

    users.append(user)
    _write_users(users)

    # never return hash
    return {"email": user["email"], "full_name": user["full_name"], "is_active": user["is_active"]}


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_email(email)
    if not user:
        return None
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return user


# -------------------------
# JWT helpers
# -------------------------
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = dict(data)
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    payload = decode_token(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"email": user["email"], "full_name": user.get("full_name", ""), "is_active": user.get("is_active", True)}

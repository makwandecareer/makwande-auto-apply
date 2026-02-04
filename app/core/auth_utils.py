import os
import json
import jwt
import tempfile
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

# Linux file locking (Render is Linux)
import fcntl

SECRET_KEY = os.getenv("SECRET_KEY", "makwande-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "data", "users.json"))
LOCK_FILE = USERS_FILE + ".lock"


def _ensure_users_file():
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _lock_handle():
    _ensure_users_file()
    os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
    fh = open(LOCK_FILE, "a+", encoding="utf-8")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    return fh


def _unlock_handle(fh):
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    finally:
        fh.close()


def _load_users_nolock() -> List[Dict[str, Any]]:
    # assumes lock already held
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        if raw == "":
            return []
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        # if file got corrupted somehow, reset safely
        return []


def _atomic_write_users_nolock(users: List[Dict[str, Any]]):
    # assumes lock already held
    folder = os.path.dirname(USERS_FILE)
    os.makedirs(folder, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(prefix="users_", suffix=".json", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, USERS_FILE)  # atomic on Linux
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    email = (email or "").strip().lower()
    if not email:
        return None

    fh = _lock_handle()
    try:
        users = _load_users_nolock()
        for u in users:
            if (u.get("email") or "").strip().lower() == email:
                return u
        return None
    finally:
        _unlock_handle(fh)


def get_password_hash(password: str) -> str:
    if not password or str(password).strip() == "":
        raise HTTPException(status_code=400, detail="Password is required")
    # DO NOT hard-limit to 72 here; bcrypt truncates but should not crash.
    return pwd_context.hash(str(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = dict(data)
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=minutes)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def create_user(email: str, password: str, full_name: Optional[str] = None) -> Dict[str, Any]:
    email = (email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    fh = _lock_handle()
    try:
        users = _load_users_nolock()

        for u in users:
            if (u.get("email") or "").strip().lower() == email:
                raise HTTPException(status_code=409, detail="User already exists")

        user = {
            "email": email,
            "full_name": full_name or "",
            "password_hash": get_password_hash(password),
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        users.append(user)
        _atomic_write_users_nolock(users)

        return {"email": user["email"], "full_name": user["full_name"], "is_active": user["is_active"]}
    finally:
        _unlock_handle(fh)


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    email = (email or "").strip().lower()
    if not email:
        return None

    fh = _lock_handle()
    try:
        users = _load_users_nolock()
        for u in users:
            if (u.get("email") or "").strip().lower() == email:
                if not u.get("is_active", True):
                    return None
                if verify_password(password, u.get("password_hash", "")):
                    return u
                return None
        return None
    finally:
        _unlock_handle(fh)


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    payload = decode_access_token(token)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {"email": user["email"], "full_name": user.get("full_name", ""), "is_active": user.get("is_active", True)}

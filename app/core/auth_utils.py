import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt  # pyjwt

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ---------------------------
# Config
# ---------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "makwande-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# IMPORTANT: Swagger "Authorize" uses this token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "users.json")
USERS_FILE = os.path.abspath(USERS_FILE)


# ---------------------------
# Models
# ---------------------------
class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


# ---------------------------
# Helpers: Users storage
# ---------------------------
def _ensure_users_file():
    folder = os.path.dirname(USERS_FILE)
    os.makedirs(folder, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)


def _load_users() -> list:
    _ensure_users_file()
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_users(users: list) -> None:
    _ensure_users_file()
    # atomic-ish write
    tmp_path = USERS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, USERS_FILE)


def _get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    users = _load_users()
    email_l = email.strip().lower()
    for u in users:
        if (u.get("email") or "").strip().lower() == email_l:
            return u
    return None


def _hash_password(password: str) -> str:
    # bcrypt limit: 72 BYTES (not chars)
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password cannot be longer than 72 bytes (bcrypt limit). Use a shorter password."
        )
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def _create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None


# ---------------------------
# Routes
# ---------------------------
@router.post("/signup")
def signup(payload: SignupRequest):
    # Guard + normalize
    email = payload.email.strip().lower()

    existing = _get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    hashed = _hash_password(payload.password)

    users = _load_users()
    users.append({
        "email": email,
        "full_name": payload.full_name or "",
        "hashed_password": hashed,
        "created_at": datetime.utcnow().isoformat() + "Z",
    })
    _save_users(users)

    return {"message": "Signup successful", "email": email}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Swagger sends:
    # username, password, grant_type, scope, client_id, client_secret
    # We treat username as email.
    email = (form_data.username or "").strip().lower()
    password = form_data.password or ""

    user = _get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not _verify_password(password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _create_access_token({"sub": email})
    return {"access_token": token, "token_type": "bearer"}


# Dependency used by protected endpoints
def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    payload = _decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Token missing subject")

    user = _get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # never return hashed_password
    return {"email": user.get("email"), "full_name": user.get("full_name", "")}


@router.get("/me")
def me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user

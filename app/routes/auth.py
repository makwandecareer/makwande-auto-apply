import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from passlib.context import CryptContext
from jose import jwt, JWTError


router = APIRouter(prefix="/api/auth", tags=["auth"])

# ----------------------------
# Config
# ----------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_TO_A_LONG_RANDOM_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ✅ Always point to app/data/users.json reliably
USERS_FILE = Path(__file__).resolve().parents[1] / "data" / "users.json"


# ----------------------------
# Helpers
# ----------------------------
def _ensure_users_file():
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")


def _load_users():
    _ensure_users_file()
    raw = USERS_FILE.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    return json.loads(raw)


def _save_users(users):
    _ensure_users_file()
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _get_user_by_email(email: str):
    users = _load_users()
    for u in users:
        if u.get("email", "").lower() == email.lower():
            return u
    return None


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token (missing subject)")
        user = _get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {"id": user["id"], "email": user["email"], "full_name": user.get("full_name", "")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ----------------------------
# Routes
# ----------------------------
@router.get("/ping")
def ping():
    return {"status": "ok", "auth": "alive"}


@router.post("/signup")
def signup(payload: dict):
    """
    Expected JSON:
    { "email": "...", "password": "...", "full_name": "..." }
    """
    try:
        email = (payload.get("email") or "").strip().lower()
        password = (payload.get("password") or "").strip()
        full_name = (payload.get("full_name") or "").strip()

        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password are required")

        users = _load_users()
        if any(u.get("email", "").lower() == email for u in users):
            raise HTTPException(status_code=400, detail="Email already registered")

        new_id = (max([u.get("id", 0) for u in users]) + 1) if users else 1
        user = {
            "id": new_id,
            "email": email,
            "full_name": full_name,
            "password_hash": _hash_password(password),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        users.append(user)
        _save_users(users)

        return {"ok": True, "id": new_id, "email": email, "full_name": full_name}

    except HTTPException:
        raise
    except Exception as e:
        # ✅ Avoid silent 500s
        raise HTTPException(status_code=500, detail=f"Signup failed: {str(e)}")


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 Password flow (Swagger popup uses this)
    username = email
    password = password
    """
    user = _get_user_by_email(form_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not _verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = _create_access_token({"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return current_user

@router.post("/signup")
def signup(payload: SignupRequest):
    email = payload.email.strip().lower()
    password = payload.password  # THIS must be a plain string

    hashed = get_password_hash(password)  # ✅ correct
    # save user with hashed password...


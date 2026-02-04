import os
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt  # pyjwt
from fastapi import Depends

router = APIRouter(prefix="/api/users", tags=["users"])

USERS_FILE = os.path.join("app", "data", "users.json")
SECRET_KEY = os.getenv("SECRET_KEY", "makwande-secret-key")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _load_users():
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None


@router.get("/me")
def me(token: str = Depends(oauth2_scheme)):
    payload = _decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Token missing email")

    users = _load_users()
    user = next((u for u in users if u.get("email") == email), None)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Never return password hashes
    return {
        "id": user.get("id"),
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "created_at": user.get("created_at"),
    }

from fastapi import APIRouter, Depends

# Reuse your auth dependency
from app.routes.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me")
def users_me(current_user=Depends(get_current_user)):
    return current_user

    from fastapi import APIRouter, Depends

from app.routes.auth import get_current_user


router = APIRouter(
    prefix="/api/users",
    tags=["Users"]
)


@router.get("/profile")
def profile(user=Depends(get_current_user)):
    return user



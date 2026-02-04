from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from fastapi.security import OAuth2PasswordBearer

from app.core.db import init_db
from app.core.users_repo import create_user, get_user_by_email, get_user_by_id
from app.core.security import verify_password, create_access_token, decode_token

# ✅ Create router
router = APIRouter(prefix="/api/auth", tags=["auth"])

# ✅ Ensure DB exists when this module is imported
init_db()

# ✅ Bearer token reader
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class SignupIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def user_public(u):
    return {
        "id": u["id"],
        "full_name": u["full_name"],
        "email": u["email"],
        "created_at": u["created_at"],
    }


def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    sub = payload.get("sub")

    if not sub or not sub.startswith("user:"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(sub.split(":", 1)[1])
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


@router.post("/signup")
def signup(payload: SignupIn):
    user = create_user(payload.full_name, payload.email, payload.password)
    token = create_access_token(subject=f"user:{user['id']}")
    return {"token": token, "user": user_public(user)}


@router.post("/login")
def login(payload: LoginIn):
    user = get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(subject=f"user:{user['id']}")
    return {"token": token, "user": user_public(user)}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {"user": user_public(user)}

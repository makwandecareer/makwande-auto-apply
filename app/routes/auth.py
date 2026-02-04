from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.core.auth_utils import create_user, authenticate_user, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


@router.post("/signup")
def signup(payload: SignupRequest):
    return create_user(payload.email, payload.password, payload.full_name)


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = (form_data.username or "").strip().lower()
    password = form_data.password

    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return current_user

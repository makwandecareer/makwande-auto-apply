import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from app.core.auth_utils import (
    create_user,
    authenticate_user,
    create_access_token,
    get_current_user,
)

logger = logging.getLogger("makwande-auto-apply")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = ""


@router.post("/signup")
def signup(payload: SignupRequest):
    """
    JSON signup:
    {
      "email": "test@makwande.co.za",
      "password": "Pass123!",
      "full_name": "Test User"
    }
    """
    try:
        user = create_user(
            email=str(payload.email),
            password=payload.password,
            full_name=payload.full_name or "",
        )
        return user
    except HTTPException:
        # Keep your intended HTTP errors (409 etc.)
        raise
    except Exception as e:
        logger.exception("Signup crashed: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Swagger "Authorize" uses x-www-form-urlencoded:
    - username (we treat as email)
    - password
    """
    try:
        user = authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token({"sub": user["email"]})
        return {"access_token": token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Login crashed: %s", e)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    """
    Returns the currently logged-in user.
    """
    return current_user

    @router.get("/me", operation_id="auth_me")
def me(current_user=Depends(get_current_user)):
    return current_user


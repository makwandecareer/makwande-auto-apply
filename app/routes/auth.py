from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth_utils import (
    SignupRequest,
    signup_user,
    authenticate_user,
    create_access_token,
    get_current_user,
    UserPublic,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=UserPublic)
def signup(payload: SignupRequest):
    return signup_user(payload)


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    # Swagger sends "username" & "password" as form-urlencoded
    user = authenticate_user(form.username, form.password)

    token = create_access_token({"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    # return safe fields only
    return {
        "email": user.get("email"),
        "full_name": user.get("full_name"),
        "is_active": user.get("is_active", True),
    }

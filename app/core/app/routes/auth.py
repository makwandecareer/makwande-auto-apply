from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

from app.db.session import get_db
from app.models.user import User
from app.services.security import create_access_token


router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ======================
# Schemas
# ======================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ======================
# Utils
# ======================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


# ======================
# Routes
# ======================

@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):

    try:
        # Check if exists
        existing = db.query(User).filter(User.email == data.email).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Create user
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password)
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        token = create_access_token({"sub": str(user.id)})

        return {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name
            },
            "token": token
        }

    except Exception as e:

        db.rollback()

        print("REGISTER ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail="Registration failed"
        )


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_access_token({"sub": str(user.id)})

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }


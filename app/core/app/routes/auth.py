import json
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt

router = APIRouter()

# Config
SECRET_KEY = os.getenv("JWT_SECRET", "changeme123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS_FILE = "app/data/users.json"


# Models
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# Helpers
def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)


def create_token(email: str):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": email,
        "exp": expire
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Routes
@router.post("/register")
def register(data: RegisterRequest):

    users = load_users()

    if any(u["email"] == data.email for u in users):
        raise HTTPException(400, "Email already registered")

    user = {
        "email": data.email,
        "password": hash_password(data.password),
        "full_name": data.full_name,
        "created_at": datetime.utcnow().isoformat()
    }

    users.append(user)
    save_users(users)

    return {"message": "Registration successful ✅"}


@router.post("/login")
def login(data: LoginRequest):

    users = load_users()

    user = next((u for u in users if u["email"] == data.email), None)

    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(data.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")

    token = create_token(user["email"])

    return {
        "access_token": token,
        "token_type": "bearer"
    }

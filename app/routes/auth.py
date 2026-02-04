from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt
import json
import os
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer

# -------------------------
# Config
# -------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "makwande-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter(prefix="/api/auth", tags=["auth"])

USERS_FILE = "app/data/users.json"


# -------------------------
# Models
# -------------------------
class SignupModel(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginModel(BaseModel):
    email: EmailStr
    password: str


# -------------------------
# Utils
# -------------------------
def load_users():
    if not os.path.exists(USERS_FILE):
        return []

    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)


def create_token(data: dict):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data.update({"exp": expire})

    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        return None


# -------------------------
# Routes
# -------------------------

@router.get("/ping")
def ping():
    return {"status": "Auth service running ✅"}


# -------------------------
# Signup
# -------------------------
@router.post("/signup")
def signup(data: SignupModel):

    users = load_users()

    for u in users:
        if u["email"] == data.email:
            raise HTTPException(400, "User already exists")

    new_user = {
        "id": len(users) + 1,
        "email": data.email,
        "full_name": data.full_name,
        "password": hash_password(data.password),
        "created_at": datetime.utcnow().isoformat()
    }

    users.append(new_user)
    save_users(users)

    return {
        "message": "Account created successfully ✅"
    }


# -------------------------
# Login
# -------------------------
@router.post("/login")
def login(data: LoginModel):

    users = load_users()

    for u in users:
        if u["email"] == data.email:

            if not verify_password(data.password, u["password"]):
                break

            token = create_token({
                "user_id": u["id"],
                "email": u["email"]
            })

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": u["id"],
                    "email": u["email"],
                    "full_name": u["full_name"]
                }
            }

    raise HTTPException(401, "Invalid login credentials")


# -------------------------
# Get Current User
# -------------------------
@router.get("/me")
def me(token: str = Depends(oauth2_scheme)):

    payload = decode_token(token)

    if not payload:
        raise HTTPException(401, "Invalid token")

    users = load_users()

    for u in users:
        if u["email"] == payload["email"]:
            return {
                "id": u["id"],
                "email": u["email"],
                "full_name": u["full_name"]
            }

    raise HTTPException(404, "User not found")


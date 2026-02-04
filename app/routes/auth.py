from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

from app.db import get_db


router = APIRouter(prefix="/api/auth", tags=["Auth"])

# ================= CONFIG =================

SECRET_KEY = "CHANGE_THIS_IN_ENV"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ================= MODELS =================

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str


# ================= HELPERS =================

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)


def hash_password(password: str):
    return pwd_context.hash(password[:72])


def create_token(data: dict, expires: Optional[timedelta] = None):
    to_encode = data.copy()

    expire = datetime.utcnow() + (expires or timedelta(minutes=15))
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ================= AUTH CORE =================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    cursor = db.cursor()
    cursor.execute(
        "SELECT id, email, full_name FROM users WHERE email=%s",
        (email,)
    )

    user = cursor.fetchone()

    if not user:
        raise credentials_exception

    return {
        "id": user[0],
        "email": user[1],
        "full_name": user[2],
    }


# ================= ROUTES =================

@router.post("/signup")
def signup(data: SignupRequest, db=Depends(get_db)):

    cursor = db.cursor()

    cursor.execute(
        "SELECT id FROM users WHERE email=%s",
        (data.email,)
    )

    if cursor.fetchone():
        raise HTTPException(409, "User already exists")

    hashed = hash_password(data.password)

    cursor.execute("""
        INSERT INTO users (email, password, full_name)
        VALUES (%s, %s, %s)
    """, (data.email, hashed, data.full_name))

    db.commit()

    return {"message": "Signup successful"}


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db)
):

    cursor = db.cursor()

    cursor.execute("""
        SELECT id, email, password
        FROM users WHERE email=%s
    """, (form.username,))

    user = cursor.fetchone()

    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(form.password, user[2]):
        raise HTTPException(401, "Invalid credentials")

    token = create_token(
        {"sub": user[1]},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserOut)
def me(current=Depends(get_current_user)):
    return current

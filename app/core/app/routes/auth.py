from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.db.session import get_conn
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

@router.post("/register")
def register(data: RegisterIn):
    email = data.email.lower().strip()

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Check existing
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            exists = cur.fetchone()
            if exists:
                raise HTTPException(status_code=409, detail="Email already registered")

            pw_hash = hash_password(data.password)

            cur.execute(
                """
                INSERT INTO users (email, password_hash, full_name)
                VALUES (%s, %s, %s)
                RETURNING id, email, full_name, created_at
                """,
                (email, pw_hash, data.full_name),
            )
            user = cur.fetchone()
        conn.commit()

    token = create_access_token({"sub": str(user["id"]), "email": user["email"]})
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "created_at": str(user["created_at"]),
        },
        "access_token": token,
        "token_type": "bearer",
    }

@router.post("/login")
def login(data: LoginIn):
    email = data.email.lower().strip()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, full_name FROM users WHERE email = %s",
                (email,),
            )
            user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user["id"]), "email": user["email"]})
    return {
        "success": True,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
        },
        "access_token": token,
        "token_type": "bearer",
    }

import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "43200"))  # 30 days default

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_access_token(payload: dict) -> str:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not set")
    exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    data = {**payload, "exp": exp}
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not set")
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

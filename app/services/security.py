import os
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

pwd = CryptContext(schemes=["bcrypt"])

SECRET = os.getenv("JWT_SECRET","dev")
ALG = os.getenv("JWT_ALGORITHM","HS256")

def hash_password(p):
    return pwd.hash(p)

def verify_password(p,h):
    return pwd.verify(p,h)

def create_token(email):
    payload = {
        "sub":email,
        "exp": datetime.utcnow()+timedelta(days=7)
    }
    return jwt.encode(payload,SECRET,algorithm=ALG)
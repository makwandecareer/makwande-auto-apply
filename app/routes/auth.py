from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.services.security import hash_password, verify_password, create_token

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register")
def register(data: dict, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email==data["email"]).first():
        raise HTTPException(400, "Email exists")

    user = User(
        full_name=data["name"],
        email=data["email"],
        password_hash=hash_password(data["password"])
    )
    db.add(user)
    db.commit()
    return {"msg":"registered"}

@router.post("/login")
def login(data: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email==data["email"]).first()
    if not user or not verify_password(data["password"], user.password_hash):
        raise HTTPException(401,"Invalid login")

    token = create_token(user.email)
    return {"access_token":token}
from sqlalchemy import Column, Integer, String, Boolean
from app.db.session import Base

class User(Base):
    __tablename__="users"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(150))
    email = Column(String(200), unique=True)
    password_hash = Column(String(255))
    is_active = Column(Boolean, default=True)
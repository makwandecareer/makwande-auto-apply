from datetime import datetime
from fastapi import HTTPException
from app.core.db import get_conn
from app.core.security import hash_password

def get_user_by_email(email: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cur.fetchone()
    conn.close()
    return row

def get_user_by_id(user_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row

def create_user(full_name: str, email: str, password: str):
    email = email.lower().strip()

    if get_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email already registered")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users(full_name, email, password_hash, created_at) VALUES(?,?,?,?)",
        (full_name.strip(), email, hash_password(password), datetime.utcnow().isoformat())
    )
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return get_user_by_id(user_id)

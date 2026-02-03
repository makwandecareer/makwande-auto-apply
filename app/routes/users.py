from fastapi import APIRouter, Header, HTTPException
from app.core.security import decode_token
from app.db.session import get_conn

router = APIRouter(prefix="/api/users", tags=["users"])

def _get_bearer_token(auth_header: str | None) -> str:
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return parts[1]

@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    token = _get_bearer_token(authorization)
    payload = decode_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, full_name, created_at, is_active FROM users WHERE id = %s",
                (int(user_id),),
            )
            user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"success": True, "user": user}


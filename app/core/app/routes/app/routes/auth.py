from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/ping")
def ping():
    return {"ok": True, "message": "auth router is mounted"}

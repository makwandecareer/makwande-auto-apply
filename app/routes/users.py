from fastapi import APIRouter

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me")
def me():
    # placeholder: will later return the authenticated user profile
    return {"ok": True, "message": "User profile endpoint ready ✅"}

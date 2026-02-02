from fastapi import APIRouter

router = APIRouter(prefix="/billing", tags=["Billing"])

@router.get("/plans")
def plans():
    return [
        {"name":"Free","price":0},
        {"name":"Premium","price":199}
    ]
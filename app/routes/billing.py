from fastapi import APIRouter

router = APIRouter(prefix="/billing", tags=["Billing"])

fetch(`${getApiBase()}/api/auth/login`)

@router.get("/plans")
def plans():
    # You can later connect to Paystack/Stripe logic.
    return {
        "currency": "ZAR",
        "plans": [
            {
                "id": "starter",
                "name": "Starter",
                "price": 0,
                "interval": "month",
                "features": [
                    "View jobs",
                    "Basic CV upload",
                    "Limited applications tracking",
                ],
            },
            {
                "id": "pro",
                "name": "Pro",
                "price": 300,
                "interval": "month",
                "features": [
                    "AI CV revamp",
                    "Cover letter generator",
                    "Application tracking dashboard",
                    "Priority job matching",
                ],
            },
            {
                "id": "business",
                "name": "Business",
                "price": 500,
                "interval": "month",
                "features": [
                    "Everything in Pro",
                    "Recruiter tools (coming soon)",
                    "Bulk CV processing (coming soon)",
                ],
            },
        ],
    }

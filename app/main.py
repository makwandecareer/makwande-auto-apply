# app/main.py
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# -----------------------------
# Logging
# -----------------------------
logger = logging.getLogger("makwande-auto-apply")
logging.basicConfig(level=logging.INFO)


# -----------------------------
# App Setup
# -----------------------------
app = FastAPI(
    title="Makwande Auto Apply Platform",
    version="1.3.0",
    description="""
Makwande Auto Apply System 🚀

A smart job application platform offering:

✅ Job boards integration & job search  
✅ Auto-Apply system  
✅ Job applications tracking  
✅ CV upload & management  
✅ AI CV Revamp (OpenAI – ATS Optimized)  
✅ AI Cover Letter Generator (OpenAI)  
✅ Secure payments via Paystack  
✅ Subscription management  
✅ User profiles (future)

Built to help jobseekers go from CV → Application → Interview.
""",
)

@app.head("/")
def head_root():
    return ""


# -----------------------------
# CORS
# -----------------------------
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in ALLOWED_ORIGINS.split(",")] if ALLOWED_ORIGINS else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Core Endpoints
# -----------------------------
@app.get("/")
def home():
    return {
        "platform": "Makwande Auto Apply",
        "status": "running ✅",
        "features": [
            "Job Boards",
            "Auto Apply",
            "Application Tracking",
            "CV Upload",
            "AI CV Revamp",
            "AI Cover Letter Generator",
            "Paystack Payments",
            "Subscriptions",
            "Future Profiles",
        ],
        "modules": {
            "job_search": "/jobs/search",
            "apply": "/jobs/apply",
            "applications": "/jobs/applications",
            "cv_upload": "/cv/upload",
            "cv_revamp_ai": "/cv/revamp",
            "cover_letter_ai": "/cv/cover-letter",
            "payments_paystack": "/billing/paystack",
            "auth": "/api/auth",
        },
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "makwande-auto-apply",
        "version": "1.3.0",
        "payments": "paystack",
        "ai_engine": "openai",
        "features": [
            "job_boards",
            "auto_apply",
            "applications_tracking",
            "cv_upload",
            "cv_revamp_ai",
            "cover_letter_ai",
            "paystack_billing",
        ],
    }


# -----------------------------
# Router Loader (Safe)
# -----------------------------
def safe_include(module_path: str, router_attr: str = "router"):
    """
    Include a router without crashing startup if it is missing.
    """
    try:
        mod = __import__(module_path, fromlist=[router_attr])
        router = getattr(mod, router_attr)
        app.include_router(router)
        logger.info("Router mounted: %s", module_path)
    except Exception as e:
        logger.warning("Could not import %s: %s", module_path, e)


# -----------------------------
# Feature Routers
# -----------------------------

# 🔐 Authentication (for future profiles & subscriptions)
safe_include("app.routes.auth")

# 💼 Job Boards + Auto Apply + Applications
safe_include("app.routes.jobs")

# 📄 CV Upload + AI Revamp + Cover Letter
safe_include("app.routes.cv")

# 🤖 AI (optional advanced processing)
safe_include("app.routes.ai")

# 💳 Paystack Billing & Subscriptions
safe_include("app.routes.billing")

# 🚫 Profiles (add later)
# safe_include("app.routes.users")


# -----------------------------
# Startup Log
# -----------------------------
@app.on_event("startup")
def startup_event():
    logger.info("==============================================")
    logger.info(" Makwande Auto Apply Platform Started 🚀")
    logger.info(" Payments: Paystack")
    logger.info(" AI: OpenAI CV Revamp & Cover Letters")
    logger.info(" Job Boards | Auto Apply | Subscriptions")
    logger.info(" Docs: /docs")
    logger.info("==============================================")

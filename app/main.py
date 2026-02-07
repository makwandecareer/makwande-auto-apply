from __future__ import annotations

import importlib
import logging
import os
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("makwande-auto-apply")

# -------------------------------------------------
# App Meta
# -------------------------------------------------
APP_NAME = "Makwande Auto Apply"
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
APP_ENV = os.getenv("APP_ENV", "production")

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Job Boards | Auto Apply | Application Tracking | "
        "OpenAI CV Revamp | OpenAI Cover Letters | Paystack Billing"
    ),
)

# -------------------------------------------------
# CORS
# -------------------------------------------------
# On Render set:
# ALLOWED_ORIGINS=https://your-frontend.vercel.app,https://yourdomain.co.za
origins_env = os.getenv("ALLOWED_ORIGINS", "*").strip()
if origins_env in ("", "*"):
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# Helpers: safe router include
# -------------------------------------------------
def safe_include(module_path: str, attr_name: str = "router", prefix: Optional[str] = None) -> None:
    """
    Import a router safely and include it without killing app startup.
    """
    try:
        mod = importlib.import_module(module_path)
        router = getattr(mod, attr_name, None)
        if router is None:
            logger.warning(f"Router missing: {module_path} has no `{attr_name}`")
            return

        if prefix:
            app.include_router(router, prefix=prefix)
        else:
            app.include_router(router)

        logger.info(f"✅ Router mounted: {module_path}")
    except Exception as e:
        logger.warning(f"⚠️ Could not import {module_path}: {e}")

# -------------------------------------------------
# Core routes
# -------------------------------------------------
@app.get("/")
def home():
    return {
        "platform": "Makwande Auto Apply",
        "env": APP_ENV,
        "status": "running ✅",
        "features": [
            "Job Boards",
            "Auto Apply",
            "Application Tracking",
            "CV Upload",
            "OpenAI CV Revamp",
            "OpenAI Cover Letter Generator",
            "Paystack Payments",
            "Subscriptions",
        ],
        "modules": {
            "auth": "/api/auth",
            "jobs": "/api/jobs",
            "match_jobs": "/api/match_jobs",
            "cv": "/cv",
            "ai_openai": "/api/ai",
            "billing_paystack": "/billing/paystack",
        },
        "docs": "/docs",
        "health": "/health",
    }

@app.head("/")
def head_root():
    return

@app.get("/health")
def health():
    return {"status": "ok", "env": APP_ENV}

@app.get("/config")
def config():
    """
    Quick diagnostics (does NOT return secrets).
    Useful to confirm Render env vars exist.
    """
    return {
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "has_paystack_secret": bool(os.getenv("PAYSTACK_SECRET_KEY")),
        "has_paystack_public": bool(os.getenv("PAYSTACK_PUBLIC_KEY")),
        "allowed_origins": allowed_origins,
    }

# -------------------------------------------------
# Mount routers (OpenAI + Paystack INCLUDED)
# -------------------------------------------------
# These must match your file paths:
# app/routes/auth.py    -> app.routes.auth
# app/routes/jobs.py    -> app.routes.jobs
# app/routes/cv.py      -> app.routes.cv
# app/routes/ai.py      -> app.routes.ai
# app/routes/billing.py -> app.routes.billing

safe_include("app.routes.auth")      # /api/auth/...
safe_include("app.routes.jobs")      # /api/jobs + /api/match_jobs
safe_include("app.routes.cv")        # /cv/upload /cv/revamp /cv/cover-letter (if you have)
safe_include("app.routes.ai")        # /api/ai/cv/revamp + /api/ai/cover-letter (OpenAI)
safe_include("app.routes.billing")   # /billing/paystack/... (Paystack)

# -------------------------------------------------
# Startup: init DB + log readiness
# -------------------------------------------------
@app.on_event("startup")
async def startup_event():
    # Jobs DB init (safe)
    try:
        from app.routes.jobs import init_jobs_db  # type: ignore
        init_jobs_db()
        logger.info("✅ Jobs DB initialized")
    except Exception as e:
        logger.warning(f"⚠️ Jobs DB init skipped: {e}")

    logger.info("=" * 60)
    logger.info(" Makwande Auto Apply Platform Started 🚀")
    logger.info(f" ENV: {APP_ENV}")
    logger.info(" Docs: /docs")
    logger.info("=" * 60)

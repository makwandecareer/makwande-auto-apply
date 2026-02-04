import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------
# Logging
# ---------------------------------------
logger = logging.getLogger("makwande-auto-apply")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------
# Create app FIRST (this fixes your crash)
# ---------------------------------------
app = FastAPI(
    title="Makwande Auto Apply",
    version="1.0.0",
    description="Makwande Auto Apply API",
)

# ---------------------------------------
# CORS (allow frontend + swagger)
# ---------------------------------------
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in ALLOWED_ORIGINS.split(",")] if ALLOWED_ORIGINS else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------
# Basic endpoints
# ---------------------------------------
@app.get("/")
def home():
    return {
        "message": "Makwande Auto Apply API is running ✅",
        "docs": "/docs",
        "health": "/health",
    }

@app.get("/health")
def health():
    return {"status": "ok"}

# ---------------------------------------
# Router mounting (AFTER app exists)
# ---------------------------------------
def safe_include(module_path: str, router_attr: str = "router"):
    """
    Loads router without crashing the app if missing.
    """
    try:
        mod = __import__(module_path, fromlist=[router_attr])
        router = getattr(mod, router_attr)
        app.include_router(router)
        logger.info(f"Router mounted: {module_path}")
    except Exception as e:
        logger.warning(f"Could not import {module_path}: {e}")

# Keep your existing routers (only if they exist)
safe_include("app.routes.auth")
safe_include("app.routes.users")
safe_include("app.routes.jobs")       # ✅ our new real jobs router
safe_include("app.routes.cv")
safe_include("app.routes.billing")

from app.routes import auth, users, jobs, cv, billing

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(cv.router)
app.include_router(billing.router)



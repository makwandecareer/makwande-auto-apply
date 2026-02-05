# app/main.py
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


logger = logging.getLogger("makwande-auto-apply")
logging.basicConfig(level=logging.INFO)


app = FastAPI(
    title="Makwande Auto Apply",
    version="1.0.0",
    description="Makwande Auto Apply API",
)

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
# Basic endpoints
# -----------------------------
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

# -----------------------------
# Routers
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

# Only mount routers this way (do NOT mount again below)
safe_include("app.routes.auth")
safe_include("app.routes.users")
safe_include("app.routes.jobs")
safe_include("app.routes.cv")
safe_include("app.routes.billing")



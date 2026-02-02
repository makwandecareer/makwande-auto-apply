import os
import sys
import logging
from typing import Optional, Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


# ---------------------------
# Logging
# ---------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | makwande-auto-apply | %(message)s",
)
log = logging.getLogger("makwande-auto-apply")


# ---------------------------
# Helpers
# ---------------------------
def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def env_str(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def safe_import(module_path: str):
    """
    Import a module safely. If it fails, log and return None.
    """
    try:
        __import__(module_path)
        return sys.modules[module_path]
    except Exception as e:
        log.warning("Could not import %s: %s", module_path, e)
        return None


def include_router_safe(module_path: str, prefix: str, tag: str):
    """
    Includes a router if it exists. Never crashes the app.
    Expects: module has `router`.
    """
    mod = safe_import(module_path)
    if not mod:
        return
    router = getattr(mod, "router", None)
    if router is None:
        log.warning("%s has no 'router' attribute", module_path)
        return
    app.include_router(router, prefix=prefix, tags=[tag])
    log.info("Router mounted: %s (%s)", module_path, prefix)


# ---------------------------
# Config
# ---------------------------
APP_ENV = env_str("APP_ENV", env_str("ENV", "production"))
DEBUG = env_bool("DEBUG", False)

OPENAI_API_KEY = env_str("OPENAI_API_KEY", env_str("OPENAI_KEY", ""))
OPENAI_MODEL = env_str("OPENAI_MODEL", "gpt-4o-mini")

ADZUNA_APP_ID = env_str("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = env_str("ADZUNA_APP_KEY", "")

DATABASE_URL = env_str("DATABASE_URL", "")

# Multi-source flags
ENABLE_ADZUNA = env_bool("ENABLE_ADZUNA", True)
ENABLE_REMOTIVE = env_bool("ENABLE_REMOTIVE", True)
ENABLE_GREENHOUSE = env_bool("ENABLE_GREENHOUSE", True)
ENABLE_LEVER = env_bool("ENABLE_LEVER", True)

# CORS
CORS_ORIGINS = env_str("CORS_ORIGINS", "*")
ALLOW_ORIGINS = [x.strip() for x in CORS_ORIGINS.split(",")] if CORS_ORIGINS else ["*"]


# ---------------------------
# App
# ---------------------------
app = FastAPI(
    title="Makwande Auto Apply",
    version="2.1.0",
    debug=DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS if ALLOW_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (optional)
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    log.info("Static mounted: %s", STATIC_DIR)


# ---------------------------
# Health checks (Render)
# ---------------------------
@app.get("/health")
@app.get("/healthz")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "makwande-auto-apply",
        "env": APP_ENV,
        "db_configured": bool(DATABASE_URL),
        "openai_configured": bool(OPENAI_API_KEY),
        "sources": {
            "adzuna": ENABLE_ADZUNA,
            "remotive": ENABLE_REMOTIVE,
            "greenhouse": ENABLE_GREENHOUSE,
            "lever": ENABLE_LEVER,
        },
        "version": "2.1.0",
    }


@app.get("/")
def root():
    # Keep it simple and always return 200
    return {"message": "Makwande Auto Apply API is running ✅", "health": "/health"}


# ---------------------------
# Global error handler
# ---------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if DEBUG else "server_error"},
    )


# ---------------------------
# Startup logs (NO DB import here)
# Because your Render Python is 3.13 and psycopg2-binary breaks there.
# We'll fix DB by pinning Python to 3.11 or moving to psycopg v3.
# ---------------------------
@app.on_event("startup")
def startup():
    log.info("Starting Makwande Auto Apply (env=%s, debug=%s)", APP_ENV, DEBUG)
    log.info("OpenAI model: %s | OpenAI key set: %s", OPENAI_MODEL, bool(OPENAI_API_KEY))
    log.info("Adzuna set: %s", bool(ADZUNA_APP_ID and ADZUNA_APP_KEY))
    log.info("DB configured: %s", bool(DATABASE_URL))
    log.info("Sources enabled: adzuna=%s remotive=%s greenhouse=%s lever=%s",
             ENABLE_ADZUNA, ENABLE_REMOTIVE, ENABLE_GREENHOUSE, ENABLE_LEVER)


# ---------------------------
# Routers (safe)
# ---------------------------
# These won't crash even if missing or DB driver errors exist.
include_router_safe("app.routes.jobs", "/api/jobs", "jobs")
include_router_safe("app.routes.cv", "/api/cv", "cv")
include_router_safe("app.routes.billing", "/api/billing", "billing")
include_router_safe("app.routes.auth", "/api/auth", "auth")
include_router_safe("app.routes.users", "/api/users", "users")


# ---------------------------
# Debug config (SAFE, no secrets)
# ---------------------------
@app.get("/api/debug/config")
def debug_config():
    return {
        "env": APP_ENV,
        "debug": DEBUG,
        "db_configured": bool(DATABASE_URL),
        "openai_configured": bool(OPENAI_API_KEY),
        "openai_model": OPENAI_MODEL,
        "adzuna_configured": bool(ADZUNA_APP_ID and ADZUNA_APP_KEY),
        "cors_origins": ALLOW_ORIGINS,
    }

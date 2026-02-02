import os
import sys
import logging
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("makwande-auto-apply")


# --- Helpers ---
def env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "y", "on")


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
        logger.warning("Could not import %s: %s", module_path, e)
        return None


# --- Config ---
APP_ENV = env_str("APP_ENV", "production")
DEBUG = env_bool("DEBUG", False)

# Render sets PORT automatically
PORT = int(os.getenv("PORT", "8000"))

# DB
DATABASE_URL = env_str("DATABASE_URL", env_str("DATABASE_URL", env_str("DB_URL", env_str("DATABASE", ""))))
# your code uses DATABASE_URL env var in session.py — keep it consistent:
# In Render, create env var: DATABASE_URL = <Render PostgreSQL External URL> (or internal if same Render network)

AUTO_CREATE_TABLES = env_bool("AUTO_CREATE_TABLES", True)

# OpenAI
OPENAI_API_KEY = env_str("OPENAI_API_KEY", env_str("OPENAI_KEY", ""))
OPENAI_MODEL = env_str("OPENAI_MODEL", "gpt-4.1-mini")  # safe default

# Adzuna
ADZUNA_APP_ID = env_str("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = env_str("ADZUNA_APP_KEY", "")

# Multi-source toggles
ENABLE_ADZUNA = env_bool("ENABLE_ADZUNA", True)
ENABLE_REMOTIVE = env_bool("ENABLE_REMOTIVE", True)
ENABLE_GREENHOUSE = env_bool("ENABLE_GREENHOUSE", True)
ENABLE_LEVER = env_bool("ENABLE_LEVER", True)

# CORS for frontend deployments
CORS_ORIGINS = env_str("CORS_ORIGINS", "*")  # set to your domains later: https://makwandecareer.co.za,https://xxx.vercel.app
ALLOW_ORIGINS = [o.strip() for o in CORS_ORIGINS.split(",")] if CORS_ORIGINS else ["*"]

# --- FastAPI App ---
app = FastAPI(
    title="Makwande Auto Apply",
    version="2.0.0",
    debug=DEBUG,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS if ALLOW_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static files (optional) ---
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    logger.info("Static mounted: %s", STATIC_DIR)

# --- Global exception handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if DEBUG else "server_error"},
    )


# --- Health checks (Render uses /healthz) ---
@app.get("/healthz")
def healthz() -> Dict[str, Any]:
    """
    Render Health Check endpoint
    """
    return {
        "status": "ok",
        "env": APP_ENV,
        "db_configured": bool(DATABASE_URL),
        "openai_configured": bool(OPENAI_API_KEY),
        "sources": {
            "adzuna": ENABLE_ADZUNA,
            "remotive": ENABLE_REMOTIVE,
            "greenhouse": ENABLE_GREENHOUSE,
            "lever": ENABLE_LEVER,
        },
    }


@app.get("/")
def root():
    # Optional: redirect to a UI page if you have it
    return RedirectResponse(url="/healthz")


# --- Startup: DB check + optional auto-create tables ---
@app.on_event("startup")
def on_startup():
    logger.info("Starting Makwande Auto Apply (env=%s, debug=%s)", APP_ENV, DEBUG)

    # Log only SAFE info (no secrets)
    logger.info("OpenAI model: %s | OpenAI key set: %s", OPENAI_MODEL, bool(OPENAI_API_KEY))
    logger.info("Adzuna set: %s", bool(ADZUNA_APP_ID and ADZUNA_APP_KEY))
    logger.info("DB configured: %s", bool(DATABASE_URL))

    # DB connectivity check (only if sqlalchemy exists and DATABASE_URL exists)
    if DATABASE_URL:
        try:
            session_mod = safe_import("app.db.session")
            if session_mod and hasattr(session_mod, "engine"):
                # ping DB
                with session_mod.engine.connect() as conn:
                    conn.execute("SELECT 1")
                logger.info("DB connection OK ✅")

            # Auto-create tables if models/base exist
            if AUTO_CREATE_TABLES:
                models_mod = safe_import("app.models.user")
                if session_mod and hasattr(session_mod, "Base"):
                    session_mod.Base.metadata.create_all(bind=session_mod.engine)
                    logger.info("DB tables ensured ✅ (AUTO_CREATE_TABLES=%s)", AUTO_CREATE_TABLES)

        except Exception as e:
            logger.error("DB startup check failed ❌: %s", e)
    else:
        logger.warning("DATABASE_URL not set — running without DB (auth/users may fail).")


# --- Routes (safe import) ---
def include_router_safe(module_path: str, attr: str = "router", prefix: str = "", tags: Optional[list] = None):
    mod = safe_import(module_path)
    if not mod:
        return
    router = getattr(mod, attr, None)
    if router is None:
        logger.warning("%s has no '%s'", module_path, attr)
        return
    app.include_router(router, prefix=prefix, tags=tags or [])
    logger.info("Router mounted: %s (%s)", module_path, prefix)


include_router_safe("app.routes.auth", prefix="/api/auth", tags=["auth"])
include_router_safe("app.routes.users", prefix="/api/users", tags=["users"])
include_router_safe("app.routes.jobs", prefix="/api/jobs", tags=["jobs"])
include_router_safe("app.routes.cv", prefix="/api/cv", tags=["cv"])
include_router_safe("app.routes.billing", prefix="/api/billing", tags=["billing"])


# --- Debug endpoint to verify env (SAFE, no keys printed) ---
@app.get("/api/debug/config")
def debug_config() -> Dict[str, Any]:
    """
    Useful to confirm Render env variables are loaded.
    Never prints secrets.
    """
    return {
        "env": APP_ENV,
        "debug": DEBUG,
        "db_configured": bool(DATABASE_URL),
        "openai_configured": bool(OPENAI_API_KEY),
        "openai_model": OPENAI_MODEL,
        "adzuna_configured": bool(ADZUNA_APP_ID and ADZUNA_APP_KEY),
        "sources": {
            "ENABLE_ADZUNA": ENABLE_ADZUNA,
            "ENABLE_REMOTIVE": ENABLE_REMOTIVE,
            "ENABLE_GREENHOUSE": ENABLE_GREENHOUSE,
            "ENABLE_LEVER": ENABLE_LEVER,
        },
        "cors_origins": ALLOW_ORIGINS,
    }


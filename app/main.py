import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends

# DB dependency
from app.db.session import get_db

# -------------------------------------------------------
# Logging
# -------------------------------------------------------
APP_NAME = "makwande-auto-apply"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(APP_NAME)

# -------------------------------------------------------
# App
# -------------------------------------------------------
ENV = os.getenv("ENV", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

app = FastAPI(
    title="Makwande Auto Apply",
    version="1.0.0",
    debug=DEBUG,
)

# -------------------------------------------------------
# CORS (adjust origins later)
# -------------------------------------------------------
origins = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------
# Static
# -------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    logger.info(f"Static mounted: {STATIC_DIR}")
else:
    logger.warning(f"Static directory not found: {STATIC_DIR}")

# -------------------------------------------------------
# Safe router loader
# -------------------------------------------------------
def safe_include(router_path: str, prefix: str = "", tags=None):
    """
    Import and include a router without breaking the whole app if import fails.
    """
    try:
        module = __import__(router_path, fromlist=["router"])
        router = getattr(module, "router")
        app.include_router(router, prefix=prefix, tags=tags or [])
        logger.info(f"Router mounted: {router_path} ({prefix or '/'})")
    except Exception as e:
        logger.warning(f"Could not import {router_path}: {e}")

# These are your routers (keep same structure)
safe_include("app.routes.auth", prefix="", tags=["Auth"])
safe_include("app.routes.users", prefix="/api", tags=["users"])
safe_include("app.routes.jobs", prefix="", tags=["Jobs"])
safe_include("app.routes.cv", prefix="", tags=["CV"])
safe_include("app.routes.billing", prefix="", tags=["Billing"])

# -------------------------------------------------------
# Base endpoints
# -------------------------------------------------------
@app.get("/")
def home():
    return {
        "message": "Makwande Auto Apply API is running ✅",
        "docs": "/docs",
        "health": "/health",
        "db_check": "/db-check",
    }

@app.get("/health")
def health():
    return {"status": "ok", "env": ENV, "debug": DEBUG}

@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    """
    Confirms DB is reachable. If this fails, auth/register/login will fail too.
    """
    db.execute(text("SELECT 1"))
    return {"db": "ok"}
    
# -------------------------------------------------------
# Startup log
# -------------------------------------------------------
@app.on_event("startup")
def on_startup():
    logger.info("====================================")
    logger.info("Starting Makwande Auto Apply")
    logger.info(f"Env: {ENV}")
    logger.info(f"Debug: {DEBUG}")
    logger.info(f"DB configured: {bool(os.getenv('DATABASE_URL'))}")
    logger.info("====================================")

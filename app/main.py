import os
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import Base, engine

Base.metadata.create_all(bind=engine)

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

APP_NAME = "Makwande Auto Apply"
ENV = os.getenv("ENV", "production")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

ADZUNA_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_KEY = os.getenv("ADZUNA_APP_KEY")

DATABASE_URL = os.getenv("DATABASE_URL")


# ---------------------------------------------------
# LOGGING
# ---------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("makwande-auto-apply")


# ---------------------------------------------------
# APP INIT
# ---------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    version="1.0.0",
    debug=DEBUG
)


# ---------------------------------------------------
# CORS (Frontend / Mobile ready)
# ---------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change later for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------
# STATIC FILES
# ---------------------------------------------------

STATIC_DIR = os.path.join("app", "static")

if os.path.exists(STATIC_DIR):
    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static"
    )
    logger.info(f"Static mounted: {os.path.abspath(STATIC_DIR)}")


# ---------------------------------------------------
# SAFE ROUTER LOADER
# ---------------------------------------------------

def safe_import(module_name: str, router_name="router"):
    """
    Import routers safely (won't crash app)
    """
    try:
        module = __import__(module_name, fromlist=[router_name])
        router = getattr(module, router_name)
        app.include_router(router)

        logger.info(f"Router mounted: {module_name}")

    except Exception as e:
        logger.warning(f"Could not import {module_name}: {e}")


# ---------------------------------------------------
# ROUTERS
# ---------------------------------------------------

ROUTERS = [
    "app.routes.auth",
    "app.routes.users",
    "app.routes.jobs",
    "app.routes.cv",
    "app.routes.billing",
]

for router in ROUTERS:
    safe_import(router)


# ---------------------------------------------------
# ROOT
# ---------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Makwande Auto Apply API is running ✅",
        "health": "/health",
        "version": "1.0.0"
    }


# ---------------------------------------------------
# HEALTH CHECK (Render)
# ---------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "env": ENV,
        "db": bool(DATABASE_URL),
        "openai": bool(OPENAI_KEY),
        "adzuna": bool(ADZUNA_ID and ADZUNA_KEY)
    }


# ---------------------------------------------------
# STARTUP EVENT
# ---------------------------------------------------

@app.on_event("startup")
async def startup():

    logger.info("====================================")
    logger.info(f"Starting {APP_NAME}")
    logger.info(f"Env: {ENV}")
    logger.info(f"Debug: {DEBUG}")

    logger.info(f"OpenAI model: {OPENAI_MODEL}")
    logger.info(f"OpenAI key set: {bool(OPENAI_KEY)}")

    logger.info(f"Adzuna set: {bool(ADZUNA_ID)}")
    logger.info(f"DB configured: {bool(DATABASE_URL)}")

    logger.info("====================================")


# ---------------------------------------------------
# GLOBAL ERROR HANDLER
# ---------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):

    logger.error(f"Unhandled error: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
        },
    )


# ---------------------------------------------------
# DEV MODE
# ---------------------------------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )

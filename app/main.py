import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.jobs import router as jobs_router
app.include_router(jobs_router)


from app.db.session import init_db

app = FastAPI(title="Makwande Auto Apply", version="1.0.0")

# CORS (safe default)
allowed = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

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

# Routers
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router

app.include_router(auth_router)
app.include_router(users_router)

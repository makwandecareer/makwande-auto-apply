from fastapi import APIRouter
from app.services.jobs import fetch_jobs

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/search")
def search(q:str):
    return fetch_jobs(q)
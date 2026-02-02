from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix="/cv", tags=["CV"])

@router.post("/upload")
def upload(file: UploadFile = File(...)):
    return {"filename":file.filename}
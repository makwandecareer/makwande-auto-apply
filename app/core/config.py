from __future__ import annotations
import os
from pydantic import BaseModel

class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Makwande Auto Apply MVP")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

settings = Settings()

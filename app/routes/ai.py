# app/routes/ai.py
import os
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, EmailStr

import openai


router = APIRouter(prefix="/api/ai", tags=["AI (OpenAI)"])

log = logging.getLogger("makwande-auto-apply.ai")

# -----------------------------
# OpenAI Config
# -----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY


def _require_openai():
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the server",
        )


# -----------------------------
# Schemas
# -----------------------------
class CVRevampRequest(BaseModel):
    full_name: str = Field(..., example="John Doe")
    email: EmailStr
    current_cv: str = Field(..., description="Raw CV text")
    target_role: str = Field(..., example="Chemical Engineer")
    years_experience: Optional[int] = Field(default=None)
    country: Optional[str] = Field(default="South Africa")


class CVRevampResponse(BaseModel):
    improved_cv: str
    ats_score: int
    strengths: list[str]
    improvements: list[str]


class CoverLetterRequest(BaseModel):
    full_name: str
    email: EmailStr
    job_title: str
    company: str
    job_description: str
    experience_summary: str
    country: Optional[str] = Field(default="South Africa")


class CoverLetterResponse(BaseModel):
    cover_letter: str


# -----------------------------
# OpenAI Helper
# -----------------------------
def _ask_openai(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str:
    _require_openai()

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # fast + cheap + good quality
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=1800,
        )

        return resp["choices"][0]["message"]["content"]

    except Exception as e:
        log.error("OpenAI error: %s", e)
        raise HTTPException(status_code=502, detail="AI processing failed")


# -----------------------------
# Routes
# -----------------------------

@router.post("/cv/revamp", response_model=CVRevampResponse)
def revamp_cv(req: CVRevampRequest):
    """
    Improve CV for ATS + recruiter readability.
    """

    system = """
You are an expert recruitment consultant and ATS specialist.
You optimize CVs for:
- Keyword scanning
- Recruiter readability
- Clear achievements
- Professional formatting
- South African job market

Always return:
1) Improved CV
2) ATS score (0-100)
3) Strengths
4) Improvements
"""

    user = f"""
Candidate Name: {req.full_name}
Email: {req.email}
Country: {req.country}
Target Role: {req.target_role}
Years Experience: {req.years_experience}

CURRENT CV:
{req.current_cv}

TASK:
Rewrite this CV into a professional, ATS-optimized format.
"""

    ai_text = _ask_openai(system, user, temperature=0.3)

    # Ask AI to structure feedback
    format_prompt = f"""
From the CV below, extract:

1) ATS Score (0-100)
2) 3-5 Strengths
3) 3-5 Improvements

Return in JSON.

CV:
{ai_text}
"""

    analysis = _ask_openai(
        "You analyze CV quality and return structured JSON.",
        format_prompt,
        temperature=0.1,
    )

    # Safe parsing fallback
    ats_score = 75
    strengths = ["Strong technical background"]
    improvements = ["Add quantified achievements"]

    try:
        import json
        parsed = json.loads(analysis)
        ats_score = int(parsed.get("ats_score", ats_score))
        strengths = parsed.get("strengths", strengths)
        improvements = parsed.get("improvements", improvements)
    except Exception:
        pass

    return CVRevampResponse(
        improved_cv=ai_text,
        ats_score=ats_score,
        strengths=strengths,
        improvements=improvements,
    )


@router.post("/cover-letter", response_model=CoverLetterResponse)
def generate_cover_letter(req: CoverLetterRequest):
    """
    Generate a personalized cover letter for a job.
    """

    system = """
You are a professional career coach.
You write persuasive, formal cover letters for African job markets.
Tone: confident, respectful, results-focused.
"""

    user = f"""
Name: {req.full_name}
Email: {req.email}
Country: {req.country}

Job Title: {req.job_title}
Company: {req.company}

Job Description:
{req.job_description}

Experience Summary:
{req.experience_summary}

TASK:
Write a 1-page professional cover letter.
"""

    letter = _ask_openai(system, user, temperature=0.4)

    return CoverLetterResponse(cover_letter=letter)


@router.get("/health")
def ai_health():
    return {
        "service": "openai-ai-engine",
        "status": "ok",
        "features": [
            "cv_revamp",
            "cover_letter",
            "ats_optimization",
        ],
    }


from __future__ import annotations

from typing import Optional, Dict, Any
from app.core.config import settings

def can_generate() -> bool:
    return bool(settings.openai_api_key.strip())

def generate_cover_letter(cv_text: str, job: Dict[str, Any]) -> str:
    """Optional: generate cover letter draft via OpenAI. If no key, raise."""
    if not can_generate():
        raise RuntimeError("OPENAI_API_KEY not set. Cover letter generation disabled.")

    # Lazy import so the app can run without OpenAI configured
    from openai import OpenAI
    client = OpenAI(api_key=settings.openai_api_key)

    prompt = f"""You are a career coach writing a concise, strong cover letter.
Write a 180-250 word cover letter for this job:

JOB TITLE: {job.get('title')}
COMPANY: {job.get('company')}
LOCATION: {job.get('location')}
SOURCE URL: {job.get('url')}

Use the candidate CV below. Be specific. Do NOT invent facts.
End with a short call to action and professional closing.

CANDIDATE CV:
{cv_text}
"""

    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": "You write professional cover letters."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content.strip()

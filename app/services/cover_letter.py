from __future__ import annotations

import os
from typing import Optional, Dict, Any

from openai import OpenAI


def _get_env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def can_generate() -> bool:
    """
    True if OpenAI is configured. (Used by UI to show Draft button.)
    """
    return bool(_get_env("OPENAI_API_KEY"))


def generate_cover_letter(
    cv_text: str,
    job_title: str,
    company: str,
    location: str,
    job_url: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generates a tailored cover letter using OpenAI.
    Requires OPENAI_API_KEY in environment.
    Optional: OPENAI_MODEL (default gpt-4o-mini)
    """
    api_key = _get_env("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = _get_env("OPENAI_MODEL", "gpt-4o-mini")

    # Safety: prevent insanely large prompts
    cv_text = (cv_text or "").strip()
    if len(cv_text) > 12000:
        cv_text = cv_text[:12000]

    client = OpenAI(api_key=api_key)

    system = (
        "You are a professional career coach and technical recruiter. "
        "Write concise, high-impact, ATS-friendly cover letters. "
        "Never invent degrees, employers, or certifications. "
        "Use confident but truthful language."
    )

    user = f"""
Write a tailored cover letter for this role.

JOB
- Title: {job_title}
- Company: {company}
- Location: {location}
- Link: {job_url}

CANDIDATE CV (raw text)
{cv_text}

REQUIREMENTS
- 250–400 words
- Professional tone
- 3 short paragraphs + bullet highlights (3–6 bullets)
- Mention role title and company name
- Close with a clear call-to-action
"""

    # If you pass additional fields later (e.g. job description), include them:
    if extra:
        jd = (extra.get("job_description") or "").strip()
        if jd:
            user += f"\n\nJOB DESCRIPTION (if provided)\n{jd[:6000]}"

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.6,
    )

    text = resp.choices[0].message.content or ""
    return text.strip()


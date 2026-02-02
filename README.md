<<<<<<< HEAD
# Makwande Auto-Apply System (MVP)

This is a **safe, legal-first MVP** for Makwande Careers:
- ✅ Collects jobs from **public / API-friendly** sources
- ✅ Matches jobs to a user's CV text (and optionally PDF/DOCX)
- ✅ Generates tailored cover letter drafts using an LLM (optional)
- ✅ Provides a simple web dashboard (FastAPI)

⚠️ **Auto-applying directly to third-party sites can violate terms of service.**
This MVP focuses on **job discovery + matching + drafting**, and can export an "apply list".
You can add employer-friendly integrations (ATS/API/email) later.

## What’s inside
- `app/main.py` – FastAPI app
- `app/services/job_sources.py` – job source connectors
- `app/services/matching.py` – matching & scoring
- `app/services/cv_parse.py` – CV parsing (txt/pdf/docx)
- `app/services/cover_letter.py` – optional LLM cover letter drafts
- `scripts/cli.py` – CLI runner (fetch + match + CSV export)

## Quick start (Windows)
1) Install Python 3.11 or 3.12
2) In a terminal inside the project folder:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000

## Enable AI cover letters (optional)
Put your API key into `.env`:

```
OPENAI_API_KEY=your_key_here
```

If no key is set, the app still works (it just won’t generate AI drafts).

## CLI example
```bash
python scripts/cli.py --query "chemical engineer" --cv data/sample_cv.txt --out data/jobs_scored.csv
```

## Next upgrades
- Better scoring using embeddings
- Employer dashboard + candidate database
- "Assisted apply" via email templates / ATS integrations
- Payments + user accounts
=======
# Makwande Careers – LiveCareer Level System

Features:
- User Auth
- CV Builder
- Job Aggregation
- AI Cover Letters
- ATS Matching
- Subscription Ready

Run:
pip install -r requirements.txt
uvicorn app.main:app --reload
>>>>>>> fdbc3e6 (Fix database connection for Render PostgreSQL)

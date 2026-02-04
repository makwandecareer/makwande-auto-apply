import json
from app.services.ai_client import chat_json

SYSTEM = """You write professional cover letters.
Return STRICT JSON with:
- subject
- cover_letter (string)
- key_points (array)
No extra keys.
"""

def generate_cover_letter(cv_text: str, job_title: str, company: str, job_description: str = ""):
    user = {
        "job_title": job_title,
        "company": company,
        "job_description": job_description[:15000],
        "cv_text": cv_text[:15000]
    }
    res = chat_json(SYSTEM, json.dumps(user, ensure_ascii=False))
    if not res["ok"]:
        return res

    try:
        data = json.loads(res["data"])
        return {"ok": True, "result": data}
    except Exception:
        return {"ok": False, "error": "AI returned invalid JSON"}

import json
from app.services.ai_client import chat_json

SYSTEM = """You are an expert ATS resume writer.
Return STRICT JSON with:
- ats_score (0-100)
- headline
- professional_summary
- core_skills (array)
- experience_bullets (array)
- achievements (array)
- education (array)
- certifications (array)
- improvements (array)
- revamped_cv_markdown (string)
No extra keys.
"""

def revamp_cv(cv_text: str, target_role: str = "", country: str = "South Africa"):
    user = {
        "country": country,
        "target_role": target_role,
        "cv_text": cv_text[:20000]
    }
    res = chat_json(SYSTEM, json.dumps(user, ensure_ascii=False))
    if not res["ok"]:
        return res

    # parse JSON string safely
    try:
        data = json.loads(res["data"])
        return {"ok": True, "result": data}
    except Exception:
        return {"ok": False, "error": "AI returned invalid JSON"}

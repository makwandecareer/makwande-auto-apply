import os
from openai import OpenAI

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

def chat_json(system: str, user: str):
    client = get_client()
    if not client:
        return {"ok": False, "error": "OPENAI_API_KEY not set"}

    # choose a safe default model you already use
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return {"ok": True, "data": resp.choices[0].message.content}

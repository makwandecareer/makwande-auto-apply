from __future__ import annotations
import re
from typing import Set

def clean_text(s: str) -> str:
    s = s or ""
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tokenize(text: str) -> Set[str]:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9+#.\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    parts = [p for p in text.split(" ") if len(p) > 1]
    return set(parts)

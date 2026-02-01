from __future__ import annotations

from pathlib import Path
from typing import Tuple

from pypdf import PdfReader
import docx

def parse_cv(path: Path) -> Tuple[str, str]:
    """Return (text, detected_type). Supports .txt, .pdf, .docx"""
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore"), "txt"

    if suffix == ".pdf":
        reader = PdfReader(str(path))
        chunks = []
        for page in reader.pages:
            try:
                chunks.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(chunks).strip(), "pdf"

    if suffix == ".docx":
        d = docx.Document(str(path))
        text = "\n".join([p.text for p in d.paragraphs])
        return text.strip(), "docx"

    raise ValueError("Unsupported CV format. Use .txt, .pdf, or .docx")

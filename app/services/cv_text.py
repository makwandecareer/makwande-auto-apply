import os

def extract_cv_text(file_path: str) -> str:
    # Try your existing parser if it exists
    try:
        from app.services.cv_parse import extract_text  # your existing file
        text = extract_text(file_path)
        return text if isinstance(text, str) else ""
    except Exception:
        pass

    # Fallback: keep system alive even if parser fails
    return ""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: Path, max_pages: int = 6) -> str:
    if not pdf_path.exists():
        return ""
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:
        return ""
    chunks = []
    for idx, page in enumerate(reader.pages[:max_pages]):
        try:
            chunks.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(chunks)

"""Extract text from PDFs. Image-only files yield an empty string."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def read_pdf(path: Path) -> str:
    text = _extract_pypdf(path)
    if text.strip():
        return text.strip()
    text = _extract_pdfplumber(path)
    return text.strip()


def _extract_pypdf(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception:
        return ""
    return "\n\n".join(pages)


def _extract_pdfplumber(path: Path) -> str:
    try:
        import pdfplumber
    except Exception:
        return ""
    try:
        with pdfplumber.open(path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception:
        return ""
    return "\n\n".join(pages)

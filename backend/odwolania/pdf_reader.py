"""Extract text from PDFs. Image-only files are read by the Tesseract path."""

from __future__ import annotations

import sys
from contextvars import ContextVar
from pathlib import Path

from pypdf import PdfReader

_MIN_CHARS_PER_PAGE = 50
# Set for the read that produced the text. Callers use it to adjust the LLM prompt.
OCR_TEXT = ContextVar("odwolania_ocr_text", default=False)


def read_pdf(path: Path) -> str:
    OCR_TEXT.set(False)
    pages = _extract_pypdf_pages(path)
    joined = "\n\n".join(pages).strip()
    if pages and not _short(pages):
        return joined
    if not joined:
        plumber = _extract_pdfplumber(path)
        if plumber and len(plumber) >= _MIN_CHARS_PER_PAGE * max(len(pages), 1):
            return plumber
    ocr = _ocr_with_pymupdf(path)
    if ocr:
        OCR_TEXT.set(True)
        return ocr
    return joined


def _short(pages: list[str]) -> bool:
    return sum(len(page.strip()) for page in pages) < _MIN_CHARS_PER_PAGE * len(pages)


def _ocr_with_pymupdf(path: Path) -> str:
    root = Path(__file__).resolve().parents[2] / "back-end2"
    if str(root) not in sys.path:
        sys.path.append(str(root))
    try:
        from pdf_reader import read_pdf as read_rendered
    except Exception:
        return ""
    try:
        document = read_rendered(path)
    except Exception:
        return ""
    if document.text_source == "ocr" and document.text.strip():
        return document.text.strip()
    return ""


def _extract_pypdf_pages(path: Path) -> list[str]:
    try:
        reader = PdfReader(str(path))
        return [page.extract_text() or "" for page in reader.pages]
    except Exception:
        return []


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

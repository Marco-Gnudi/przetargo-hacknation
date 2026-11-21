"""Read PDF text with PyMuPDF. OCR is optional and never required."""

import shutil
from dataclasses import dataclass, field

import pymupdf

from normalizers import clean_text, collapse_spaced_letters, compact


@dataclass
class PdfDocument:
    path: str
    pages: list = field(default_factory=list)
    text: str = ""
    needs_ocr: bool = False
    ocr_used: bool = False

    @property
    def flat(self):
        return compact(self.text)


def read_pdf(path):
    document = pymupdf.open(path)
    pages = []
    chunks = []
    for index, page in enumerate(document):
        text = clean_text(page.get_text("text") or "")
        pages.append({"number": index + 1, "text": text, "char_count": len(text.strip())})
        chunks.append(text)
    document.close()
    text = collapse_spaced_letters("\n".join(chunks))
    needs_ocr = sum(page["char_count"] for page in pages) < 30
    ocr_used = False
    if needs_ocr and shutil.which("tesseract"):
        ocr_text = _try_ocr(path)
        if ocr_text:
            text = collapse_spaced_letters(ocr_text)
            ocr_used = True
            needs_ocr = False
    return PdfDocument(str(path), pages, text, needs_ocr, ocr_used)


def _try_ocr(path):
    try:
        import pytesseract
    except ImportError:
        return ""
    document = pymupdf.open(path)
    parts = []
    for page in document:
        pixmap = page.get_pixmap(dpi=200)
        try:
            from PIL import Image
            import io
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            parts.append(pytesseract.image_to_string(image, lang="pol+eng"))
        except Exception:
            document.close()
            return ""
    document.close()
    return clean_text("\n".join(parts))

"""Read PDF text with PyMuPDF. A short text layer is sent through Tesseract."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
from dotenv import load_dotenv

from normalizers import clean_text, collapse_spaced_letters, compact
from ocr_cleanup import cleanup_ocr

# PSM 4 and 6 tied on skany 0001 (19/28 gold strings). These pages are one block, so PSM 6 stays.
OCR_PSM = 6
_OCR_CACHE_VERSION = "v1"
_MIN_CHARS_PER_PAGE = 50
_ENV_PATH = Path(__file__).resolve().parents[1] / "backend" / ".env"
_CACHE: dict[tuple, PdfDocument] = {}


@dataclass
class PdfDocument:
    path: str
    pages: list = field(default_factory=list)
    text: str = ""
    needs_ocr: bool = False
    ocr_used: bool = False
    text_source: str = "text"
    ocr_seconds: float = 0.0

    @property
    def flat(self):
        return compact(self.text)


def read_pdf(path):
    resolved = Path(path).resolve()
    stat = resolved.stat()
    key = (str(resolved), stat.st_mtime_ns, stat.st_size, OCR_PSM)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    document = _read(resolved)
    _CACHE[key] = document
    return document


def _read(path: Path) -> PdfDocument:
    pdf = pymupdf.open(path)
    pages = []
    chunks = []
    for index, page in enumerate(pdf):
        text = clean_text(page.get_text("text") or "")
        pages.append({"number": index + 1, "text": text, "char_count": len(text.strip())})
        chunks.append(text)
    layer = collapse_spaced_letters("\n".join(chunks))
    if not _layer_is_short(pages):
        pdf.close()
        return PdfDocument(str(path), pages, layer, False, False, "text", 0.0)
    cached = _load_ocr_cache(path)
    if cached is not None:
        pdf.close()
        return PdfDocument(str(path), pages, cached["text"], False, True, "ocr", cached["seconds"])
    started = time.perf_counter()
    ocr_text = _ocr_pages(pdf)
    elapsed = round(time.perf_counter() - started, 2)
    pdf.close()
    if not ocr_text.strip():
        return PdfDocument(str(path), pages, layer, True, False, "text", elapsed)
    cleaned = collapse_spaced_letters(cleanup_ocr(ocr_text))
    _save_ocr_cache(path, cleaned, elapsed)
    return PdfDocument(str(path), pages, cleaned, False, True, "ocr", elapsed)


def _ocr_cache_file(path: Path) -> Path:
    stat = path.stat()
    token = f"{path}|{stat.st_mtime_ns}|{stat.st_size}|{OCR_PSM}|{_OCR_CACHE_VERSION}"
    digest = hashlib.sha256(token.encode()).hexdigest()
    folder = Path(__file__).resolve().parents[1] / "backend" / ".cache" / "ocr"
    return folder / f"{digest}.json"


def _load_ocr_cache(path: Path) -> dict | None:
    file = _ocr_cache_file(path)
    if not file.is_file():
        return None
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or "text" not in payload:
        return None
    return payload


def _save_ocr_cache(path: Path, text: str, seconds: float) -> None:
    file = _ocr_cache_file(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(
        json.dumps({"text": text, "seconds": seconds}, ensure_ascii=False),
        encoding="utf-8",
    )


def _layer_is_short(pages: list[dict]) -> bool:
    if not pages:
        return True
    return sum(page["char_count"] for page in pages) < _MIN_CHARS_PER_PAGE * len(pages)


def _ocr_pages(pdf) -> str:
    if not _configure_tesseract():
        return ""
    import pytesseract
    from PIL import Image

    parts = []
    for page in pdf:
        dpi = _render_dpi(pdf, page)
        pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        image = _prepare(image)
        try:
            parts.append(
                pytesseract.image_to_string(
                    image,
                    lang="pol",
                    config=f"--psm {OCR_PSM}",
                )
            )
        except Exception:
            parts.append("")
    return clean_text("\n".join(parts))


def _render_dpi(pdf, page) -> int:
    dpi = 300.0
    for image in page.get_images(full=True):
        try:
            info = pdf.extract_image(image[0])
        except Exception:
            continue
        if page.rect.width:
            native = info["width"] / (page.rect.width / 72.0)
            if native > dpi:
                dpi = native
    return int(round(dpi))


def _prepare(image):
    from PIL import ImageOps

    gray = ImageOps.autocontrast(image.convert("L"))
    gray = _deskew(gray)
    # Lift the paper to white and leave the ink, including grey strokes.
    return gray.point(lambda pixel: 255 if pixel > 210 else pixel)


def _deskew(image):
    """Try a few small angles and keep the one with the strongest text lines."""
    small = image.resize((max(1, image.width // 4), max(1, image.height // 4)))
    best_angle = 0.0
    best_score = -1
    for angle in (0, -0.5, 0.5, -1, 1, -1.5, 1.5, -2, 2):
        rotated = small if angle == 0 else small.rotate(angle, fillcolor=255, expand=False)
        score = _line_score(rotated)
        if score > best_score:
            best_score = score
            best_angle = angle
    if abs(best_angle) < 0.4:
        return image
    from PIL import Image

    return image.rotate(best_angle, fillcolor=255, expand=True, resample=Image.Resampling.BICUBIC)


def _line_score(image) -> int:
    pixels = image.tobytes()
    width, height = image.size
    score = 0
    for top in range(0, height, 2):
        row = pixels[top * width:(top + 1) * width]
        ink = sum(1 for pixel in row if pixel < 128)
        score += ink * ink
    return score


def _configure_tesseract() -> bool:
    load_dotenv(_ENV_PATH)
    try:
        import pytesseract
    except ImportError:
        return False
    command = os.environ.get("TESSERACT_CMD") or ""
    if not (command and Path(command).is_file()):
        found = shutil.which("tesseract")
        candidates = [Path(found)] if found else []
        local = Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tesseract.exe"
        program = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        candidates.extend((local, program))
        command = next((str(path) for path in candidates if path.is_file()), "")
    if not command:
        return False
    pytesseract.pytesseract.tesseract_cmd = command
    bundled = Path(command).resolve().parent / "tessdata"
    user_data = Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tessdata"
    for folder in (bundled, user_data):
        if (folder / "pol.traineddata").is_file():
            # This build opens $TESSDATA_PREFIX/<lang>.traineddata directly.
            os.environ["TESSDATA_PREFIX"] = str(folder)
            return True
    return True

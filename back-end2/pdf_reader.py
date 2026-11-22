"""Read PDF text with PyMuPDF. A short text layer is sent through Tesseract."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
from dotenv import load_dotenv

from normalizers import clean_text, collapse_spaced_letters, compact
from ocr_cleanup import cleanup_ocr

# Tesseract's OpenMP threads thrash when several pages are OCR'd at once (parallel
# requests or evaluation workers): a 3 s page can take over 10 minutes.
os.environ.setdefault("OMP_THREAD_LIMIT", "1")

# PSM 4 and 6 tied on skany 0001 (19/28 gold strings). These pages are one block, so PSM 6 stays.
OCR_PSM = 6
_OCR_CACHE_VERSION = "v5-rot"
_MIN_CHARS_PER_PAGE = 50
_PAGE_TIMEOUT_SECONDS = 90
_ENV_PATH = Path(__file__).resolve().parents[1] / "backend" / ".env"
_LOCAL_TESSDATA = Path(__file__).resolve().parent / "models" / "tessdata"
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
    ocr_confidence: float | None = None

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
    short = [index for index, page in enumerate(pages) if page["char_count"] < _MIN_CHARS_PER_PAGE]
    if not short:
        pdf.close()
        return PdfDocument(str(path), pages, layer, False, False, "text", 0.0)
    if not _layer_is_short(pages):
        return _read_mixed(path, pdf, pages, chunks, short)
    cached = _load_ocr_cache(path)
    if cached is not None:
        pdf.close()
        cleaned = collapse_spaced_letters(cleanup_ocr(cached["text"]))
        return PdfDocument(str(path), pages, cleaned, False, True, "ocr", cached["seconds"])
    started = time.perf_counter()
    ocr_text = clean_text("\n".join(_ocr_pages(pdf)))
    elapsed = round(time.perf_counter() - started, 2)
    pdf.close()
    if not ocr_text.strip():
        return PdfDocument(str(path), pages, layer, True, False, "text", elapsed)
    # The cache keeps raw Tesseract output so cleanup changes apply without a re-OCR.
    _save_ocr_cache(path, ocr_text, elapsed)
    cleaned = collapse_spaced_letters(cleanup_ocr(ocr_text))
    return PdfDocument(str(path), pages, cleaned, False, True, "ocr", elapsed)


def _read_mixed(path: Path, pdf, pages: list[dict], chunks: list[str], short: list[int]) -> PdfDocument:
    """A digital PDF with some scanned pages: OCR only the pages without a text layer."""
    cached = _load_ocr_cache(path, "pages")
    if cached is not None and isinstance(cached.get("pages"), dict):
        scanned = {int(index): text for index, text in cached["pages"].items()}
        elapsed = cached["seconds"]
    else:
        started = time.perf_counter()
        scanned = dict(zip(short, _ocr_pages(pdf, short)))
        elapsed = round(time.perf_counter() - started, 2)
        _save_ocr_cache(path, "", elapsed, "pages", {str(index): text for index, text in scanned.items()})
    pdf.close()
    if not any(text.strip() for text in scanned.values()):
        layer = collapse_spaced_letters("\n".join(chunks))
        return PdfDocument(str(path), pages, layer, True, False, "text", elapsed)
    merged = [
        cleanup_ocr(clean_text(scanned[index])) if index in scanned else chunk
        for index, chunk in enumerate(chunks)
    ]
    text = collapse_spaced_letters("\n".join(merged))
    return PdfDocument(str(path), pages, text, False, True, "ocr", elapsed)


def _tessdata_dir() -> Path | None:
    """A folder holding a better pol.traineddata, e.g. tessdata_best. Falls back to the system model."""
    load_dotenv(_ENV_PATH)
    candidates = [os.environ.get("OCR_TESSDATA") or "", str(_LOCAL_TESSDATA)]
    for candidate in candidates:
        if candidate and (Path(candidate) / "pol.traineddata").is_file():
            return Path(candidate)
    return None


def _model_tag() -> str:
    folder = _tessdata_dir()
    if folder is None:
        return "system"
    return f"{folder}|{(folder / 'pol.traineddata').stat().st_size}"


def _ocr_cache_file(path: Path, variant: str = "") -> Path:
    stat = path.stat()
    token = f"{path}|{stat.st_mtime_ns}|{stat.st_size}|{OCR_PSM}|{_OCR_CACHE_VERSION}|{_model_tag()}"
    if variant:
        token += f"|{variant}"
    digest = hashlib.sha256(token.encode()).hexdigest()
    folder = Path(__file__).resolve().parents[1] / "backend" / ".cache" / "ocr"
    return folder / f"{digest}.json"


def _load_ocr_cache(path: Path, variant: str = "") -> dict | None:
    file = _ocr_cache_file(path, variant)
    if not file.is_file():
        return None
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or "text" not in payload:
        return None
    return payload


def mean_ocr_confidence(path) -> float | None:
    """Mean Tesseract word confidence for a scan, cached next to the OCR text."""
    path = Path(path)
    cached = _load_ocr_cache(path)
    if cached and isinstance(cached.get("confidence"), (int, float)):
        return float(cached["confidence"])
    document = read_pdf(path)
    if document.text_source != "ocr":
        return None
    score = _measure_confidence(path)
    if score is None:
        return None
    cached = _load_ocr_cache(path)
    if cached is not None:
        cached["confidence"] = score
        file = _ocr_cache_file(path)
        file.write_text(json.dumps(cached, ensure_ascii=False), encoding="utf-8")
    document.ocr_confidence = score
    return score


def _measure_confidence(path: Path) -> float | None:
    if not _configure_tesseract():
        return None
    import pytesseract
    from PIL import Image

    scores = []
    pdf = pymupdf.open(path)
    try:
        for page in pdf:
            dpi = _render_dpi(pdf, page)
            pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            image = _prepare(image)
            try:
                data = pytesseract.image_to_data(
                    image,
                    lang="pol",
                    config=f"--psm {OCR_PSM}",
                    output_type=pytesseract.Output.DICT,
                    timeout=_PAGE_TIMEOUT_SECONDS,
                )
            except Exception:
                continue
            for conf in data.get("conf", []):
                try:
                    value = float(conf)
                except (TypeError, ValueError):
                    continue
                if value >= 0:
                    scores.append(value)
    finally:
        pdf.close()
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)


def _save_ocr_cache(path: Path, text: str, seconds: float, variant: str = "", pages: dict | None = None) -> None:
    file = _ocr_cache_file(path, variant)
    file.parent.mkdir(parents=True, exist_ok=True)
    payload = {"text": text, "seconds": seconds}
    if pages is not None:
        payload["pages"] = pages
    file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _layer_is_short(pages: list[dict]) -> bool:
    if not pages:
        return True
    return sum(page["char_count"] for page in pages) < _MIN_CHARS_PER_PAGE * len(pages)


def _ocr_pages(pdf, indexes: list[int] | None = None) -> list[str]:
    """Raw Tesseract text for each requested page (all pages by default)."""
    wanted = list(range(len(pdf))) if indexes is None else indexes
    if not _configure_tesseract():
        return ["" for _ in wanted]
    from PIL import Image

    config = f"--psm {OCR_PSM}"
    folder = _tessdata_dir()
    if folder is not None:
        config += f' --tessdata-dir "{folder}"'
    parts = []
    document_angle = 0
    for position, index in enumerate(wanted):
        page = pdf[index]
        dpi = _render_dpi(pdf, page)
        pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
        image = _prepare(Image.open(io.BytesIO(pixmap.tobytes("png"))))
        if document_angle:
            image = image.rotate(-document_angle, expand=True, fillcolor=255)
        text = _tesseract(image, config)
        # Upside-down pages still yield word-like tokens, so the first page is always checked.
        if position == 0 or _word_share(text) < 0.35:
            best_angle, best_share = 0, _word_share(text)
            # Low-confidence OSD guesses are often wrong, so a page that still reads badly tries every right angle.
            guess = _osd_angle(image)
            # OSD mixes up 90 and 270, so a sideways guess is checked against its opposite.
            flipped = (guess + 180) % 360 if guess in (90, 270) else None
            for angle in dict.fromkeys(a for a in (guess, flipped, 90, 180, 270) if a is not None):
                if angle == 0:
                    continue
                if angle not in (guess, flipped) and best_share >= 0.35:
                    break
                second = _tesseract(image.rotate(-angle, expand=True, fillcolor=255), config)
                if _word_share(second) > best_share:
                    text, best_angle, best_share = second, angle, _word_share(second)
            if position == 0:
                document_angle = best_angle
        parts.append(text)
    return parts


def _tesseract(image, config: str) -> str:
    import pytesseract

    try:
        return pytesseract.image_to_string(image, lang="pol", config=config, timeout=_PAGE_TIMEOUT_SECONDS)
    except Exception:
        return ""


def _word_share(text: str) -> float:
    """Share of tokens that look like words; a sideways page OCRs to short fragments."""
    tokens = text.split()
    if len(tokens) < 5:
        return 0.0
    words = [token for token in tokens if re.fullmatch(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]{3,}[.,:;]?", token)]
    return len(words) / len(tokens)


def _osd_angle(image) -> int:
    """Clockwise degrees that make the page upright, from Tesseract's orientation detection."""
    import pytesseract

    folder = _tessdata_dir()
    osd_config = "--psm 0 -c min_characters_to_try=5"
    if folder is not None and (folder / "osd.traineddata").is_file():
        osd_config += f' --tessdata-dir "{folder}"'
    try:
        found = pytesseract.image_to_osd(
            image, config=osd_config, output_type=pytesseract.Output.DICT, timeout=_PAGE_TIMEOUT_SECONDS
        )
    except Exception:
        return 0
    return int(found.get("rotate") or 0) % 360


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

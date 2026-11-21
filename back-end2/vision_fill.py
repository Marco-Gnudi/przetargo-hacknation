"""Fill weak scans from a page image. Text PDFs never reach the model."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

import pymupdf

from checksums import repair_nip, repair_nrb, repair_pesel, repair_regon

LOW_CONFIDENCE = 60.0
_CACHE = Path(__file__).resolve().parents[1] / "backend" / ".cache" / "vision"
_STATS_LOCK = threading.Lock()
_STATS = {"calls": 0, "cache_hits": 0, "errors": 0}

_TEMPLATES = {
    "odwolanie": {
        "OdwolanieKIO": {
            "data": None,
            "czynnosc_dzien": None,
            "czynnosc_powod_id": None,
            "czynnosc_opis": None,
            "miejscowosc": None,
        },
        "Odwolujacy": [{
            "krs": None,
            "nazwa": None,
            "nip": None,
            "regon": None,
            "przez-pelnomocnika": None,
            "pelnomocnik": {"imie_nazwisko": None, "nazwa": None, "mail": None},
        }],
        "Zamawiajacy": [{
            "krs": None,
            "nazwa": None,
            "nip": None,
            "regon": None,
            "prowadzacy_postepowanie": None,
        }],
        "ZamowieniePubliczne": {
            "numer_bzp": None,
            "numer_postepowania": None,
            "numer_ted": None,
            "tytul": None,
        },
    },
    "pelnomocnictwo": {
        "mocodawca": [{
            "data": {
                "imie_nazwisko": None,
                "krs": None,
                "nazwa": None,
                "nip": None,
                "typ": None,
            },
            "podpisujacy": [{"imie_nazwisko": None}],
        }],
        "pelnomocnicy": [{"imie_nazwisko": None, "pesel": None}],
    },
    "przelew": {
        "przelew_bankowy": {
            "data_operacji": None,
            "kwota": None,
            "na_rachunek": None,
            "numer_transakcji": None,
            "tytul": None,
            "z_rachunku": None,
        }
    },
}

_PROMPT = (
    "Wypełnij szablon JSON na podstawie skanu.\n"
    "Kopiuj wartości dosłownie, razem z polskimi znakami.\n"
    "Nazwy osób podaj w mianowniku. Nazwy firm przepisz tak, jak są napisane, bez skracania.\n"
    "Tytuł przepisz w całości.\n"
    "Liczby i daty przepisz znak po znaku.\n"
    "Gdy pola nie da się odczytać, wpisz null. Nie zgaduj.\n"
    "Szablon:\n"
)


def reset_vision_stats() -> None:
    with _STATS_LOCK:
        _STATS.update(calls=0, cache_hits=0, errors=0)


def vision_stats() -> dict[str, int]:
    with _STATS_LOCK:
        return dict(_STATS)


def apply_vision(pdf_path, payload: dict, document_type: str) -> dict:
    """After rules and the text model, read the page only when the scan is weak."""
    if document_type not in _TEMPLATES or not isinstance(payload, dict):
        return payload
    from pdf_reader import mean_ocr_confidence, read_pdf

    document = read_pdf(pdf_path)
    if document.text_source != "ocr":
        return payload
    confidence = document.ocr_confidence
    if not _weak(document_type, payload, confidence):
        confidence = mean_ocr_confidence(pdf_path)
        if not _weak(document_type, payload, confidence):
            return payload
    try:
        images = _render(Path(pdf_path), document_type)
        raw = _cached_reply(document_type, images)
    except Exception:
        _bump("errors")
        return payload
    if not raw:
        return payload
    try:
        from odwolania.llm_extractor import normalise_vision

        shaped = normalise_vision(document_type, raw)
    except Exception:
        _bump("errors")
        return payload
    return merge_vision(payload, shaped)


def needs_vision(document_type: str, payload: dict, *, text_source: str, confidence: float | None) -> bool:
    if text_source != "ocr" or document_type not in _TEMPLATES:
        return False
    return _weak(document_type, payload, confidence)


def merge_vision(base, incoming):
    """Keep a present valid value. Vision may fill a null or replace a failed identifier."""
    return _merge(base, incoming, "")


def _weak(document_type: str, payload: dict, confidence: float | None) -> bool:
    if confidence is not None and confidence < LOW_CONFIDENCE:
        return True
    if _missing_required(document_type, payload):
        return True
    return _has_invalid_identifier(payload)


def _missing_required(document_type: str, payload: dict) -> bool:
    if document_type == "przelew":
        body = payload.get("przelew_bankowy") or {}
        return any(_blank(body.get(key)) for key in (
            "data_operacji", "kwota", "na_rachunek", "z_rachunku", "tytul", "numer_transakcji",
        ))
    if document_type == "odwolanie":
        header = payload.get("OdwolanieKIO") or {}
        if any(_blank(header.get(key)) for key in (
            "data", "czynnosc_dzien", "czynnosc_powod_id", "czynnosc_opis", "miejscowosc",
        )):
            return True
        appellant = (payload.get("Odwolujacy") or [{}])[0] or {}
        authority = (payload.get("Zamawiajacy") or [{}])[0] or {}
        order = payload.get("ZamowieniePubliczne") or {}
        return _blank(appellant.get("nazwa")) or _blank(authority.get("nazwa")) or _blank(order.get("tytul"))
    if document_type == "pelnomocnictwo":
        for principal in payload.get("mocodawca") or [{}]:
            data = (principal or {}).get("data") or {}
            if _blank(data.get("nazwa")) and _blank(data.get("imie_nazwisko")):
                return True
            signers = (principal or {}).get("podpisujacy") or []
            if not signers or _blank((signers[0] or {}).get("imie_nazwisko")):
                return True
        agents = payload.get("pelnomocnicy") or []
        return not agents or _blank((agents[0] or {}).get("imie_nazwisko"))
    return False


def _has_invalid_identifier(payload) -> bool:
    found = False

    def walk(node, key=""):
        nonlocal found
        if found:
            return
        if isinstance(node, dict):
            for child, value in node.items():
                if _identifier_failed(child, value):
                    found = True
                    return
                walk(value, child)
        elif isinstance(node, list):
            for item in node:
                walk(item, key)

    walk(payload)
    return found


def _identifier_failed(key: str, value) -> bool:
    if _blank(value):
        return False
    if key == "nip":
        return repair_nip(value) is None
    if key == "regon":
        return repair_regon(value) is None
    if key == "pesel":
        return repair_pesel(value) is None
    if key in {"na_rachunek", "z_rachunku"}:
        return repair_nrb(value) is None
    if key == "krs":
        digits = "".join(char for char in str(value) if char.isdigit())
        return len(digits) != 10
    if key == "czynnosc_powod_id":
        return value not in range(1, 13)
    return False


def _merge(base, incoming, key: str):
    if isinstance(base, dict) and isinstance(incoming, dict):
        merged = dict(base)
        for child, value in incoming.items():
            if child not in merged:
                merged[child] = value
            else:
                merged[child] = _merge(merged[child], value, child)
        return merged
    if isinstance(base, list) and isinstance(incoming, list):
        merged = list(base)
        for index, item in enumerate(incoming):
            if index < len(merged):
                merged[index] = _merge(merged[index], item, key)
            elif _useful(item):
                merged.append(item)
        return merged
    if _blank(base) or _identifier_failed(key, base):
        return base if _blank(incoming) else incoming
    return base


def _useful(value) -> bool:
    if isinstance(value, dict):
        return any(_useful(item) for item in value.values())
    if isinstance(value, list):
        return any(_useful(item) for item in value)
    return not _blank(value)


def _blank(value) -> bool:
    return value is None or value == ""


def _render(path: Path, document_type: str) -> list[bytes]:
    pdf = pymupdf.open(path)
    try:
        limit = 2 if document_type == "odwolanie" else min(pdf.page_count, 3)
        pages = []
        for index, page in enumerate(pdf):
            if index >= limit:
                break
            pages.append(page.get_pixmap(dpi=200, alpha=False).tobytes("png"))
        return pages
    finally:
        pdf.close()


def _cached_reply(document_type: str, images: list[bytes]) -> dict:
    from odwolania.llm import LLMClient, cache_skipped

    client = LLMClient()
    digest = hashlib.sha256()
    digest.update(client.model.encode("utf-8"))
    digest.update(b"\0")
    digest.update(document_type.encode("utf-8"))
    for image in images:
        digest.update(b"\0")
        digest.update(image)
    path = _CACHE / f"{digest.hexdigest()}.json"
    if path.is_file() and not cache_skipped():
        _bump("cache_hits")
        cached = json.loads(path.read_text(encoding="utf-8"))
        return cached if isinstance(cached, dict) else {}
    prompt = _PROMPT + json.dumps(_TEMPLATES[document_type], ensure_ascii=False, indent=2)
    _bump("calls")
    raw = client.extract_vision(prompt, images)
    if raw:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return raw


def _bump(name: str) -> None:
    with _STATS_LOCK:
        _STATS[name] = _STATS.get(name, 0) + 1

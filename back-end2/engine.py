"""One extraction call shared by the web API and the batch CLI."""

from __future__ import annotations

from pathlib import Path

from llm_fill import extract_mistral_only, fill_with_mistral, review_marks, tag_rules
from odwolania.llm import LLMAuthError, current_usage, set_llm_document
from pdf_reader import OCR_MISSING_HINT, read_pdf
from pipeline import load_rules, process_pdf

MODES = ("regular", "mistral", "mistral_only")
MODE_ALIASES = {
    "deterministic": "regular",
    "hybrid": "mistral",
    "llm-only": "mistral_only",
    "mistral-only": "mistral_only",
}
LLM_MODES = ("mistral", "mistral_only")
RULES = load_rules()


def normalise_mode(name: str) -> str:
    mode = MODE_ALIASES.get((name or "").strip().lower(), (name or "").strip().lower())
    if mode not in MODES:
        raise ValueError(f"Unknown mode {name!r}. Use deterministic, hybrid or llm-only.")
    return mode


def extract_document(path: Path, filename: str, mode: str, rules: dict | None = None) -> dict:
    """Classify and extract one PDF. Raises LLMAuthError when the model endpoint refuses the key."""
    set_llm_document(filename)
    before = current_usage()
    try:
        item = _extract(Path(path), filename, mode, rules or RULES)
    except LLMAuthError:
        raise
    except Exception:
        item = envelope(filename, {}, None, "The PDF could not be read.")
    item["llm"] = _usage_delta(before, current_usage())
    if mode in LLM_MODES and item["llm"]["failures"]:
        item["warnings"].append(
            f"{item['llm']['failures']} Mistral request(s) failed; those fields kept the deterministic value or null."
        )
    return item


def _extract(path: Path, filename: str, mode: str, rules: dict) -> dict:
    if mode == "mistral_only":
        document = read_pdf(path)
        payload, document_type, sources, raw = extract_mistral_only(path)
        diagnostic = {
            "document_type": document_type,
            "warnings": [OCR_MISSING_HINT] if document.needs_ocr else [],
            "file": filename,
            "text_source": document.text_source,
            "ocr_seconds": document.ocr_seconds,
            "needs_ocr": document.needs_ocr,
        }
        item = envelope(filename, payload, diagnostic, None)
        item["sources"] = sources
        item["raw"] = raw
        return item
    payload, diagnostic = process_pdf(path, rules)
    diagnostic["file"] = filename
    sources = tag_rules(payload)
    raw = payload
    mistral: dict = {}
    if mode == "mistral":
        try:
            payload, document_type, sources, mistral, raw = fill_with_mistral(
                path, payload, diagnostic["document_type"]
            )
            diagnostic = dict(diagnostic)
            diagnostic["document_type"] = document_type
        except LLMAuthError:
            raise
        except Exception:
            diagnostic = dict(diagnostic)
            diagnostic["warnings"] = list(diagnostic.get("warnings") or []) + [
                "Mistral fill failed; deterministic values were kept."
            ]
            raw = payload
            mistral = {}
    item = envelope(filename, payload, diagnostic, None)
    item["sources"] = sources
    item["raw"] = raw
    if mode == "mistral":
        item["review"] = review_marks(payload, sources, mistral)
    return item


def envelope(filename, payload, diagnostic, error, status=None) -> dict:
    document_type = diagnostic["document_type"] if diagnostic else "unknown"
    needs_ocr = bool(diagnostic and diagnostic.get("needs_ocr"))
    if status is None:
        if error:
            status = "error"
        elif document_type == "unknown":
            # Unread is not the same as "not one of our document types".
            status = "needs_ocr" if needs_ocr else "unrecognized"
        else:
            status = "ok"
    return {
        "filename": filename,
        "document_type": document_type,
        "status": status,
        "result": payload if isinstance(payload, dict) else {},
        "warnings": list(diagnostic["warnings"]) if diagnostic else [],
        "error": error,
        "text_source": diagnostic.get("text_source") if diagnostic else None,
        "ocr_seconds": diagnostic.get("ocr_seconds") if diagnostic else None,
        "needs_ocr": needs_ocr,
    }


def _usage_delta(before: dict, after: dict) -> dict:
    return {key: int(after.get(key, 0)) - int(before.get(key, 0)) for key in ("calls", "prompt_tokens", "completion_tokens", "failures")}

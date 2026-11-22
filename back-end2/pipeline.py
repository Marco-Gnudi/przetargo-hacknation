"""Run classification and extraction for one PDF."""

import json
from pathlib import Path

from classifier import classify
from extractors import EXTRACTORS
from pdf_reader import OCR_MISSING_HINT, ocr_available, read_pdf
from validators import validate

RULES_PATH = Path(__file__).resolve().parent / "configs" / "rules.json"


def load_rules(path=None):
    source = Path(path) if path else RULES_PATH
    return json.loads(source.read_text(encoding="utf-8"))


def process_pdf(path, rules=None):
    rules = rules or load_rules()
    document = read_pdf(path)
    decision = classify(document, rules)
    document_type = decision["document_type"]
    warnings = []
    if document.needs_ocr:
        warnings.append(OCR_MISSING_HINT if not ocr_available() else "Scanned PDF: OCR found no readable text.")
    if document.ocr_used:
        warnings.append(f"Text came from OCR ({document.ocr_seconds:.1f} s).")
    try:
        if document_type == "unknown":
            payload = {}
        else:
            payload = EXTRACTORS[document_type](document, rules)
    except Exception as exc:
        payload = {}
        warnings.append(f"Extraction failed: {exc}")
        document_type = "unknown"
    warnings.extend(validate(document_type, payload))
    diagnostic = {
        "file": str(path),
        "document_type": document_type,
        "confident": decision["confident"],
        "reason": decision["reason"],
        "scores": decision["scores"],
        "warnings": warnings,
        "text_source": document.text_source,
        "ocr_seconds": document.ocr_seconds,
        "needs_ocr": document.needs_ocr,
    }
    return payload, diagnostic

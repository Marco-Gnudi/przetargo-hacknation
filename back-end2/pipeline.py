"""Run classification and extraction for one PDF."""

import json
from pathlib import Path

from classifier import classify
from extractors import EXTRACTORS
from pdf_reader import read_pdf
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
        warnings.append("No usable text layer and OCR did not run.")
    if document.ocr_used:
        warnings.append("Text came from the optional Tesseract fallback.")
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
    }
    return payload, diagnostic

"""Walk case folders of PDFs and write one JSON per file."""

from __future__ import annotations

import json
from pathlib import Path

from odwolania.classifier import classify
from odwolania.extractors.przelew import extract_przelew
from odwolania.pdf_reader import read_pdf


def extract(document_type: str, text: str) -> dict:
    if document_type == "przelew":
        return extract_przelew(text).data
    return {}


def process_document(pdf_path: Path) -> dict:
    text = read_pdf(pdf_path)
    document_type = classify(text)
    if document_type is None:
        return {}
    return extract(document_type, text)


def run(input_dir: Path, output_dir: Path) -> list[Path]:
    """Write <output>/<case>/<pdf stem>.json for each <input>/<case>/*.pdf."""
    written: list[Path] = []
    for case_dir in _case_dirs(input_dir):
        pdfs = sorted(case_dir.glob("*.pdf"))
        if not pdfs:
            continue
        out_case = output_dir / case_dir.name
        out_case.mkdir(parents=True, exist_ok=True)
        for pdf in pdfs:
            payload = process_document(pdf)
            dest = out_case / f"{pdf.stem}.json"
            dest.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            written.append(dest)
    return written


def _case_dirs(input_dir: Path) -> list[Path]:
    return sorted(path for path in input_dir.iterdir() if path.is_dir())

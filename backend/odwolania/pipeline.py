"""Walk case folders of PDFs and write one JSON per file."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from odwolania.classifier import classify
from odwolania.extractors.przelew import extract_przelew
from odwolania.llm_extractor import extract as extract_llm
from odwolania.pdf_reader import read_pdf

_LLM_TYPES = ("odwolanie", "pelnomocnictwo")


def extract(document_type: str, text: str) -> dict:
    if document_type == "przelew":
        return extract_przelew(text).data
    if document_type in _LLM_TYPES:
        return extract_llm(document_type, text).data
    return {}


def process_document(pdf_path: Path) -> dict:
    text = read_pdf(pdf_path)
    document_type = classify(text)
    if document_type is None:
        return {}
    return extract(document_type, text)


@dataclass(frozen=True)
class ProcessedFile:
    filename: str
    document_type: str | None
    data: dict
    sources: dict[str, str]
    raw: dict | None = None


def process_file(
    pdf_path: Path,
    *,
    mode: str = "regular",
    filename: str | None = None,
    document_type: str | None = None,
) -> ProcessedFile:
    """Classify and extract one PDF. `regular` never calls the LLM.

    `bielik` fills from the model after the rules. `bielik_only` never runs
    a deterministic extractor: every value comes from the model.
    A known `document_type` (e.g. from back-end2's classifier) skips classification.
    """
    if mode not in ("regular", "bielik", "bielik_only"):
        raise ValueError("mode must be regular, bielik, or bielik_only")
    text = read_pdf(pdf_path)
    use_llm = mode != "regular"
    document_type = document_type or classify(text)
    if document_type is None:
        return ProcessedFile(filename or pdf_path.name, None, {}, {})
    if mode == "bielik_only":
        extracted = extract_llm(document_type, text)
        return ProcessedFile(
            filename or pdf_path.name,
            document_type,
            extracted.data,
            extracted.sources,
            extracted.raw if extracted.raw is not None else extracted.data,
        )
    data, sources, raw = _extract(document_type, text, use_llm=use_llm)
    return ProcessedFile(filename or pdf_path.name, document_type, data, sources, raw)


def _extract(document_type: str, text: str, *, use_llm: bool) -> tuple[dict, dict[str, str], dict]:
    if document_type == "przelew":
        extracted = extract_przelew(text, use_llm=use_llm)
        return extracted.data, extracted.sources, extracted.data
    if use_llm and document_type in _LLM_TYPES:
        extracted = extract_llm(document_type, text)
        return extracted.data, extracted.sources, extracted.raw if extracted.raw is not None else extracted.data
    return {}, {}, {}


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

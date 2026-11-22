"""PrzetarGO batch CLI: every PDF under input/ becomes a JSON file with the same relative path under output/.

    python main.py                                   # input/ -> output/, hybrid when a key is set
    python main.py --mode deterministic              # rules and local OCR only, no API calls
    MISTRAL_API_KEY=... python main.py --mode hybrid # rules, then Mistral for the gaps

The web page (start.sh / start.bat) calls the same engine.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "back-end2"))

# Scaleway list price for mistral-small-3.2-24b-instruct-2506, EUR per million tokens.
PRICE_INPUT_EUR = 0.15
PRICE_OUTPUT_EUR = 0.35


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn KIO case PDFs into JSON (input/<case>/x.pdf -> output/<case>/x.json).")
    parser.add_argument("--input", type=Path, default=ROOT / "input", help="Folder of PDFs, searched recursively (default: input/).")
    parser.add_argument("--output", type=Path, default=ROOT / "output", help="Where JSON files are written (default: output/).")
    parser.add_argument(
        "--mode",
        default="auto",
        help="auto (default: hybrid when MISTRAL_API_KEY is set, else deterministic), deterministic, hybrid, or llm-only.",
    )
    parser.add_argument("--workers", type=int, default=int(os.environ.get("PRZETARGO_WORKERS", "4")), help="Parallel documents (default 4).")
    args = parser.parse_args(argv)

    from engine import LLM_MODES, extract_document, normalise_mode
    from odwolania.llm import LLMAuthError, LLMClient, llm_setting, start_usage
    from pdf_reader import forget_pdf, ocr_available

    if sys.version_info < (3, 13):
        print(f"Warning: Python {sys.version.split()[0]} found; the challenge requires 3.13+.", file=sys.stderr)
    if not args.input.exists():
        print(f"Input not found: {args.input}", file=sys.stderr)
        return 2

    requested = args.mode.strip().lower()
    has_key = bool(llm_setting("LLM_API_KEY"))
    if requested == "auto":
        mode = "mistral" if has_key else "regular"
    else:
        try:
            mode = normalise_mode(requested)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 2

    if mode in LLM_MODES:
        problem = _check_llm(LLMClient) if has_key else "MISTRAL_API_KEY is not set"
        if problem:
            if requested != "auto":
                print(f"Mistral is not usable: {problem}. Fix it or run with --mode deterministic.", file=sys.stderr)
                return 2
            print(f"Mistral is not usable ({problem}); continuing in deterministic mode.", file=sys.stderr)
            mode = "regular"

    model = llm_setting("LLM_MODEL") if mode in LLM_MODES else None
    print(f"Mode: {_mode_label(mode)}" + (f" ({model} at {llm_setting('LLM_BASE_URL')})" if model else ""))
    ocr = ocr_available()
    print("OCR: Tesseract ready" if ocr else "OCR: Tesseract not found - scanned PDFs cannot be read (run python doctor.py)")

    source = args.input
    root = source if source.is_dir() else source.parent
    output = args.output.resolve()
    pdfs = sorted(
        path for path in (source.rglob("*") if source.is_dir() else [source])
        if path.is_file() and path.suffix.lower() == ".pdf" and output not in path.resolve().parents
    )
    if not pdfs:
        print(f"No PDF files in {source}.")
        return 0

    log_path = output / "_logs" / "processing.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    key_rejected = threading.Event()
    started = time.perf_counter()

    def run(pdf: Path) -> dict:
        start_usage()
        relative = _relative(pdf, root)
        destination = output / relative.with_suffix(".json")
        doc_started = time.perf_counter()
        current = "regular" if key_rejected.is_set() else mode
        try:
            item = extract_document(pdf, pdf.name, current)
        except LLMAuthError:
            key_rejected.set()
            item = extract_document(pdf, pdf.name, "regular")
            item["warnings"].append("Mistral rejected the API key; this file used deterministic extraction only.")
        finally:
            forget_pdf(pdf)
        item["seconds"] = round(time.perf_counter() - doc_started, 2)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(item["result"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        record = {
            "file": relative.as_posix(),
            "output": destination.relative_to(output).as_posix(),
            "document_type": item["document_type"],
            "status": item["status"],
            "seconds": item["seconds"],
            "text_source": item["text_source"],
            "ocr_seconds": item["ocr_seconds"],
            "llm": item.get("llm"),
            "warnings": item["warnings"],
            "error": item["error"],
        }
        with lock:
            log.write(json.dumps(record, ensure_ascii=False) + "\n")
            log.flush()
            print(f"  {item['status']:<12} {item['document_type']:<15} {item['seconds']:>6.1f}s  {relative.as_posix()}")
        return record

    print(f"Processing {len(pdfs)} PDF(s) with {max(1, args.workers)} worker(s)...")
    with log_path.open("w", encoding="utf-8") as log, ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        records = list(pool.map(run, pdfs))

    _summary(records, time.perf_counter() - started, output, log_path, key_rejected.is_set())
    return 1 if any(record["status"] == "error" for record in records) else 0


def _check_llm(client_class) -> str:
    """One tiny request before the batch, so a bad key fails in seconds, not after 150 files."""
    try:
        client_class().ping()
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        return f"the API answered HTTP {status}" if status else f"could not reach the API endpoint ({type(exc).__name__})"
    return ""


def _mode_label(mode: str) -> str:
    return {"regular": "deterministic", "mistral": "hybrid (rules + Mistral)", "mistral_only": "llm-only (Mistral)"}[mode]


def _summary(records: list[dict], elapsed: float, output: Path, log_path: Path, key_rejected: bool) -> None:
    count = len(records)
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for record in records:
        by_status[record["status"]] = by_status.get(record["status"], 0) + 1
        by_type[record["document_type"]] = by_type.get(record["document_type"], 0) + 1
    ocr_files = [record for record in records if record["text_source"] == "ocr"]
    ocr_seconds = sum(record["ocr_seconds"] or 0 for record in ocr_files)
    llm = {key: sum((record["llm"] or {}).get(key, 0) for record in records) for key in ("calls", "prompt_tokens", "completion_tokens", "failures")}

    print()
    print(f"Done: {count} PDF(s) in {elapsed:.1f} s ({elapsed / count:.2f} s per file). JSON is in {output}.")
    print("  Types:  " + ", ".join(f"{name} {total}" for name, total in sorted(by_type.items())))
    print("  Status: " + ", ".join(f"{name} {total}" for name, total in sorted(by_status.items())))
    if ocr_files:
        print(f"  OCR:    {len(ocr_files)} scanned file(s), {ocr_seconds:.1f} s of Tesseract time")
    if llm["calls"] or llm["failures"]:
        cost = (llm["prompt_tokens"] * PRICE_INPUT_EUR + llm["completion_tokens"] * PRICE_OUTPUT_EUR) / 1_000_000
        print(
            f"  Mistral: {llm['calls']} request(s), {llm['failures']} failed, "
            f"{llm['prompt_tokens']} prompt + {llm['completion_tokens']} completion tokens (about EUR {cost:.3f} at Scaleway prices)"
        )
    if key_rejected:
        print("  WARNING: Mistral rejected the API key during the run; later files used deterministic extraction only.")
    unread = [record["file"] for record in records if record["status"] in ("needs_ocr", "error")]
    if unread:
        print(f"  WARNING: {len(unread)} file(s) could not be read and were written as {{}}:")
        for name in unread[:20]:
            print(f"    {name}")
    print(f"  Details: {log_path}")


def _relative(pdf: Path, root: Path) -> Path:
    try:
        return pdf.relative_to(root)
    except ValueError:
        return Path(pdf.name)


if __name__ == "__main__":
    raise SystemExit(main())

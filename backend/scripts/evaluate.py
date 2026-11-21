"""Score extraction against the UZP expected JSON.

Run from the repo:
    python backend/scripts/evaluate.py --mode regular
    python backend/scripts/evaluate.py --mode bielik --cache on
    python backend/scripts/evaluate.py --data UZP-hacknation-task/dane/skany --mode regular

Ground truth is only an expected JSON that sits next to the PDF. A file with
no JSON, including negatives and decoys, is expected to produce {}.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "back-end2"))
sys.path.insert(1, str(ROOT / "backend"))

from llm_fill import extract_bielik_only, fill_with_bielik  # noqa: E402
from normalizers import account_number, amount, compact  # noqa: E402
from pipeline import load_rules, process_pdf  # noqa: E402
from odwolania.config import task_data_dir  # noqa: E402
from odwolania.llm import current_usage, load_env, set_skip_cache, start_usage  # noqa: E402

_JSON_BY_PDF = {"potwierdzenie_przelewu.pdf": "przelew.json"}
_TYPE_BY_NAME = {
    "odwolanie.pdf": "odwolanie",
    "pelnomocnictwo.pdf": "pelnomocnictwo",
    "potwierdzenie_przelewu.pdf": "przelew",
}
_TYPE_BY_FOLDER = {
    "odwolania": "odwolanie",
    "pelnomocnictwa": "pelnomocnictwo",
    "potwierdzenia": "przelew",
}
_ID_LEAVES = {"na_rachunek", "z_rachunku", "nip", "krs", "regon", "pesel"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate extraction against UZP JSON.")
    parser.add_argument("--data", type=Path, default=None, help="Folder of PDFs (default: dane/)")
    parser.add_argument("--mode", choices=("regular", "bielik", "bielik_only"), required=True)
    parser.add_argument("--cache", choices=("on", "off"), default="on")
    args = parser.parse_args(argv)

    data = args.data if args.data is not None else task_data_dir() / "dane"
    if not data.is_dir():
        print(f"Data directory not found: {data}", file=sys.stderr)
        return 2

    load_env()
    start_usage()
    set_skip_cache(args.cache == "off")
    from vision_fill import reset_vision_stats, vision_stats

    reset_vision_stats()
    rules = load_rules()
    pdfs = sorted(data.rglob("*.pdf"))
    started = time.perf_counter()
    if args.mode == "regular" or len(pdfs) < 2:
        rows = []
        for index, pdf in enumerate(pdfs, start=1):
            rows.append(_score_pdf(pdf, args.mode, rules))
            if index % 25 == 0 or index == len(pdfs):
                print(f"  {index}/{len(pdfs)}", flush=True)
    else:
        rows = _score_parallel(pdfs, args.mode, rules)
    elapsed = time.perf_counter() - started
    summary = _summarise(rows)
    usage = current_usage()
    summary["mode"] = args.mode
    summary["cache"] = args.cache
    summary["data"] = str(data)
    summary["tokens"] = usage
    summary["seconds"] = round(elapsed, 1)
    summary["seconds_per_document"] = round(elapsed / len(pdfs), 2) if pdfs else 0
    summary["vision"] = vision_stats()
    written = _write_reports(args.mode, summary, rows)
    _print(summary, rows, written)
    return 0


def _score_parallel(pdfs: list[Path], mode: str, rules: dict) -> list[dict]:
    """Up to four documents at once. HTTP 429 is retried inside the client."""
    rows: list[dict | None] = [None] * len(pdfs)
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}

    def job(pdf: Path) -> tuple[dict, dict]:
        start_usage()
        return _score_pdf(pdf, mode, rules), current_usage()

    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(job, pdf): index for index, pdf in enumerate(pdfs)}
        for future in as_completed(futures):
            row, usage = future.result()
            rows[futures[future]] = row
            for key in totals:
                totals[key] += usage.get(key, 0)
            done += 1
            if done % 25 == 0 or done == len(pdfs):
                print(f"  {done}/{len(pdfs)}", flush=True)
    bucket = current_usage()
    for key in totals:
        bucket[key] = bucket.get(key, 0) + totals[key]
    return rows


def _gold_path(pdf: Path) -> Path:
    sibling = pdf.with_name(_JSON_BY_PDF.get(pdf.name, f"{pdf.stem}.json"))
    if sibling.is_file():
        return sibling
    shared = pdf.parent.parent / "ground_truth_json" / f"{pdf.stem}.json"
    if shared.is_file():
        return shared
    return sibling


def _score_pdf(pdf: Path, mode: str, rules: dict) -> dict:
    gold_path = _gold_path(pdf)
    gold = json.loads(gold_path.read_text(encoding="utf-8")) if gold_path.is_file() else {}
    if not isinstance(gold, dict):
        gold = {}
    got, text_source = _predict(pdf, mode, rules)
    mismatches = []
    tp = fp = fn = 0
    expected_leaves = dict(_leaves(gold))
    got_leaves = dict(_leaves(got))
    paths = list(expected_leaves) + [path for path in got_leaves if path not in expected_leaves]
    for path in paths:
        expected = expected_leaves.get(path)
        actual = got_leaves.get(path)
        match = _same(path, expected, actual)
        if match and _present(expected):
            tp += 1
        elif not match:
            if _present(expected):
                fn += 1
            if _present(actual):
                fp += 1
            mismatches.append({
                "file": pdf.as_posix(),
                "field": path,
                "expected": expected,
                "got": actual,
                "text_source": text_source,
            })
    return {
        "file": pdf,
        "type": _document_type(pdf, gold),
        "split": _split(pdf, gold),
        "text_source": text_source,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "mismatches": mismatches,
    }


def _predict(pdf: Path, mode: str, rules: dict) -> tuple[dict, str]:
    if mode == "bielik_only":
        from pdf_reader import read_pdf

        document = read_pdf(pdf)
        payload, _document_type, _sources, _raw = extract_bielik_only(pdf)
        return payload if isinstance(payload, dict) else {}, document.text_source
    payload, diagnostic = process_pdf(pdf, rules)
    source = diagnostic.get("text_source") or "text"
    if mode == "bielik":
        payload, _document_type, _sources, _bielik, _raw = fill_with_bielik(
            pdf, payload, diagnostic["document_type"]
        )
    return payload if isinstance(payload, dict) else {}, source


def _leaves(value, prefix=""):
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _leaves(item, path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _leaves(item, f"{prefix}[{index}]")
    elif prefix:
        yield prefix, value


def _present(value) -> bool:
    return value is not None and value != ""


def _same(path: str, expected, actual) -> bool:
    left, right = _normalise(path, expected), _normalise(path, actual)
    if left is None or right is None:
        return left is right
    if isinstance(left, float) and isinstance(right, float):
        return left == right
    return left == right


def _normalise(path: str, value):
    """Apply the same leaf normalisation the extractors use on their output."""
    if not _present(value):
        return None
    leaf = re.sub(r"\[\d+\]", "", path.split(".")[-1])
    if leaf in {"na_rachunek", "z_rachunku"}:
        return account_number(str(value)) or compact(str(value))
    if leaf in _ID_LEAVES:
        digits = re.sub(r"\D", "", str(value))
        return digits or compact(str(value))
    if leaf == "kwota":
        parsed = amount(value)
        return float(parsed) if parsed is not None else compact(str(value))
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return compact(value)
    return value


def _split(pdf: Path, gold: dict) -> str:
    if "skany" in pdf.parts:
        return "scan"
    if not gold:
        return "negative"
    return "text"


def _document_type(pdf: Path, gold: dict) -> str:
    if "skany" in pdf.parts and pdf.parent.name in _TYPE_BY_FOLDER:
        return _TYPE_BY_FOLDER[pdf.parent.name]
    if pdf.name in _TYPE_BY_NAME:
        return _TYPE_BY_NAME[pdf.name]
    if not gold:
        return "negative"
    if "przelew_bankowy" in gold:
        return "przelew"
    if "OdwolanieKIO" in gold or "Odwolujacy" in gold:
        return "odwolanie"
    if "mocodawca" in gold or "pelnomocnicy" in gold:
        return "pelnomocnictwo"
    return "other"


def _summarise(rows: list[dict]) -> dict:
    def pack(selected):
        tp = sum(row["tp"] for row in selected)
        fp = sum(row["fp"] for row in selected)
        fn = sum(row["fn"] for row in selected)
        if tp == fp == fn == 0:
            precision = recall = f1 = 1.0 if selected else 0.0
        else:
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {
            "n": len(selected),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
        }

    summary = {"overall": pack(rows), "splits": {}, "types": {}}
    for name in ("text", "scan", "negative"):
        summary["splits"][name] = pack([row for row in rows if row["split"] == name])
    types = sorted({row["type"] for row in rows})
    for doc_type in types:
        chosen = [row for row in rows if row["type"] == doc_type]
        summary["types"][doc_type] = pack(chosen)
        for name in ("text", "scan", "negative"):
            summary["types"][doc_type][name] = pack([row for row in chosen if row["split"] == name])
    return summary


def _write_reports(mode: str, summary: dict, rows: list[dict]) -> tuple[Path, Path]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = ROOT / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    mismatches = [item for row in rows for item in row["mismatches"]]
    payload = dict(summary)
    payload["mismatches"] = mismatches
    json_path = folder / f"eval_{mode}_{stamp}.json"
    csv_path = folder / f"eval_{mode}_{stamp}.csv"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("file", "field", "expected", "got", "text_source"))
        writer.writeheader()
        for item in mismatches:
            writer.writerow({
                "file": item["file"],
                "field": item["field"],
                "expected": "" if item["expected"] is None else item["expected"],
                "got": "" if item["got"] is None else item["got"],
                "text_source": item["text_source"],
            })
    return json_path, csv_path


def _print(summary: dict, rows: list[dict], written: tuple[Path, Path]) -> None:
    usage = summary["tokens"]
    print(f"mode {summary['mode']}  cache {summary['cache']}  files {summary['overall']['n']}")
    print(
        f"tokens  calls={usage['calls']}  "
        f"prompt={usage['prompt_tokens']}  completion={usage['completion_tokens']}"
    )
    vision = summary.get("vision") or {}
    print(
        f"vision  calls={vision.get('calls', 0)}  "
        f"cache_hits={vision.get('cache_hits', 0)}  errors={vision.get('errors', 0)}"
    )
    print(
        f"time  seconds={summary.get('seconds', 0)}  "
        f"per_document={summary.get('seconds_per_document', 0)}"
    )
    print()
    _table(["group", "n", "P", "R", "F1"], [
        [name, bucket["n"], bucket["precision"], bucket["recall"], bucket["f1"]]
        for name, bucket in (("all", summary["overall"]), *summary["splits"].items())
    ])
    print()
    type_rows = []
    for doc_type, bucket in summary["types"].items():
        type_rows.append([doc_type, bucket["n"], bucket["precision"], bucket["recall"], bucket["f1"]])
    _table(["type", "n", "P", "R", "F1"], type_rows)
    print()
    cross = []
    for doc_type, bucket in summary["types"].items():
        for name in ("text", "scan"):
            part = bucket[name]
            if part["n"]:
                cross.append([doc_type, name, part["n"], part["precision"], part["recall"], part["f1"]])
    _table(["type", "split", "n", "P", "R", "F1"], cross)
    print()
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        for item in row["mismatches"]:
            counts[re.sub(r"\[\d+\]", "[]", item["field"])] += 1
    print("10 most common failing fields")
    for field, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:10]:
        print(f"  {count:4d}  {field}")
    print()
    print(f"wrote {written[0]}")
    print(f"wrote {written[1]}")


def _table(header: list[str], rows: list[list]) -> None:
    rendered = [[str(cell) for cell in row] for row in rows]
    widths = [len(cell) for cell in header]
    for row in rendered:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    line = "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(header))
    print(line)
    print("  ".join("-" * width for width in widths))
    for row in rendered:
        print("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))


if __name__ == "__main__":
    raise SystemExit(main())

"""Write Mistral-only JSON for every training PDF.

Run from backend/:
    python scripts/export_mistral_outputs.py
    python scripts/export_mistral_outputs.py --force

Reads UZP-hacknation-task/dane/przyklad_*/ and negatywne/. Writes
outputs_mistral/<case>/<expected-json-name>.json at the repo root.
Saved model replies in backend/.cache/llm/ are reused. A file whose output
already exists is skipped, so a second run makes no LLM calls. --force
rewrites those files and still uses the cache.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from odwolania.config import REPO_ROOT, task_data_dir
from odwolania.llm import current_usage, set_llm_document, set_skip_cache, start_usage
from odwolania.pipeline import process_file

_OUTPUT_NAME = {
    "odwolanie.pdf": "odwolanie.json",
    "pelnomocnictwo.pdf": "pelnomocnictwo.json",
    "potwierdzenie_przelewu.pdf": "przelew.json",
}
_COLUMNS = ("case", "file", "detected type", "fields filled", "tokens used")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Export Mistral-only JSON for manual review.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rewrite outputs that already exist. Still uses the LLM cache.",
    )
    args = parser.parse_args(argv)

    dane = task_data_dir() / "dane"
    out_root = REPO_ROOT / "outputs_mistral"
    _refuse_task_dir(out_root)
    pdfs = _pdfs(dane)
    previous = _read_summary(out_root / "summary.csv")
    start_usage()
    set_skip_cache(False)
    rows: list[dict[str, str]] = []
    total = len(pdfs)

    for index, pdf in enumerate(pdfs, start=1):
        case = pdf.parent.name
        filename = _output_name(pdf)
        dest = out_root / case / filename
        _refuse_task_dir(dest)
        label = f"[{index}/{total}] {case}/{filename}"
        if dest.is_file() and not args.force:
            row = previous.get((case, filename)) or _row_from_file(case, filename, dest)
            rows.append(row)
            print(f"{label} skip", flush=True)
            continue
        set_llm_document(pdf.name)
        before = current_usage()
        try:
            processed = process_file(pdf, mode="mistral_only")
        except Exception as exc:
            print(f"{label} ERROR {type(exc).__name__}", flush=True)
            continue
        spent = _delta(before, current_usage())
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            json.dumps(processed.data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        filled = _filled(processed.data)
        row = {
            "case": case,
            "file": filename,
            "detected type": processed.document_type or "",
            "fields filled": str(filled),
            "tokens used": str(spent["prompt_tokens"] + spent["completion_tokens"]),
        }
        rows.append(row)
        print(
            f"{label} type={row['detected type'] or '-'} filled={filled} "
            f"calls={spent['calls']} tokens={row['tokens used']}",
            flush=True,
        )

    _write_summary(out_root / "summary.csv", rows)
    usage = current_usage()
    print(
        f"LLM calls {usage['calls']}  "
        f"prompt_tokens {usage['prompt_tokens']}  "
        f"completion_tokens {usage['completion_tokens']}",
        flush=True,
    )
    return 0


def _pdfs(dane: Path) -> list[Path]:
    cases = sorted(path for path in dane.glob("przyklad_*") if path.is_dir())
    negatives = dane / "negatywne"
    if negatives.is_dir():
        cases.append(negatives)
    found: list[Path] = []
    for case in cases:
        found.extend(sorted(case.glob("*.pdf")))
    return found


def _output_name(pdf: Path) -> str:
    return _OUTPUT_NAME.get(pdf.name, f"{pdf.stem}.json")


def _filled(value: object) -> int:
    if isinstance(value, dict):
        return sum(_filled(item) for item in value.values())
    if isinstance(value, list):
        return sum(_filled(item) for item in value)
    if value is None or value == "":
        return 0
    return 1


def _delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {key: after[key] - before[key] for key in ("prompt_tokens", "completion_tokens", "calls")}


def _row_from_file(case: str, filename: str, dest: Path) -> dict[str, str]:
    try:
        payload = json.loads(dest.read_text(encoding="utf-8"))
        filled = _filled(payload)
    except (OSError, json.JSONDecodeError):
        filled = 0
    return {
        "case": case,
        "file": filename,
        "detected type": "",
        "fields filled": str(filled),
        "tokens used": "0",
    }


def _read_summary(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {(row["case"], row["file"]): row for row in csv.DictReader(handle)}


def _write_summary(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _refuse_task_dir(path: Path) -> None:
    task = task_data_dir().resolve()
    resolved = path.resolve()
    if resolved == task or task in resolved.parents:
        raise SystemExit(f"Refusing to write into the task folder: {resolved}")


if __name__ == "__main__":
    raise SystemExit(main())

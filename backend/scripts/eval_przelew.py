"""Compare extracted przelew JSON with przyklad_01..60 expected files.

Run from backend/: python scripts/eval_przelew.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from odwolania.classifier import classify
from odwolania.config import task_data_dir
from odwolania.extractors.przelew import FIELDS, extract_przelew
from odwolania.pdf_reader import read_pdf


def _same(field: str, got: object, expected: object) -> bool:
    if field == "kwota":
        if got is None or expected is None:
            return got is expected
        return abs(float(got) - float(expected)) < 0.001
    return got == expected


def main() -> int:
    dane = task_data_dir() / "dane"
    hits = {field: 0 for field in FIELDS}
    mismatches: list[str] = []
    source_hits = {field: {"rule": 0, "llm": 0} for field in FIELDS}
    cases = 0

    for index in range(1, 61):
        case = dane / f"przyklad_{index:02d}"
        pdf = case / "potwierdzenie_przelewu.pdf"
        expected = json.loads((case / "przelew.json").read_text(encoding="utf-8"))
        expected_fields = expected["przelew_bankowy"]
        text = read_pdf(pdf)
        if classify(text) != "przelew":
            got_fields = {field: None for field in FIELDS}
            sources = {field: "llm" for field in FIELDS}
        else:
            extracted = extract_przelew(text)
            got_fields = extracted.data["przelew_bankowy"]
            sources = extracted.sources
        cases += 1
        for field in FIELDS:
            source_hits[field][sources.get(field, "llm")] += 1
            if _same(field, got_fields.get(field), expected_fields.get(field)):
                hits[field] += 1
                continue
            mismatches.append(
                f"przyklad_{index:02d} {field} source={sources.get(field)}\n"
                f"  got:      {got_fields.get(field)!r}\n"
                f"  expected: {expected_fields.get(field)!r}"
            )

    print(f"cases {cases}")
    for field in FIELDS:
        pct = 100.0 * hits[field] / cases
        rule = source_hits[field]["rule"]
        llm = source_hits[field]["llm"]
        print(f"  {field}: {hits[field]}/{cases} = {pct:.1f}%  (rule={rule}, llm={llm})")
    correct = sum(hits.values())
    total = cases * len(FIELDS)
    print(f"fields {correct}/{total} = {100.0 * correct / total:.1f}%")
    print(f"mismatches: {len(mismatches)}")
    for line in mismatches:
        print(line)
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Score Bielik extraction of odwolanie and pelnomocnictwo against training JSON.

Run from backend/:
    python scripts/eval_llm.py --limit 5
    python scripts/eval_llm.py
    python scripts/eval_llm.py --type odwolanie

Responses are cached in backend/.cache/llm/ by prompt and text, so a rerun
does not call the model again.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from odwolania.config import task_data_dir
from odwolania.pipeline import process_file

_TYPES = ("odwolanie", "pelnomocnictwo")
_PDF = {"odwolanie": "odwolanie.pdf", "pelnomocnictwo": "pelnomocnictwo.pdf"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Bielik JSON extraction.")
    parser.add_argument("--limit", type=int, default=None, help="Only the first N cases")
    parser.add_argument("--type", choices=_TYPES, default=None, help="Only this document type")
    args = parser.parse_args(argv)

    dane = task_data_dir() / "dane"
    selected = (args.type,) if args.type else _TYPES
    last = 60 if args.limit is None else min(60, args.limit)
    stats = {
        doc_type: {"n": 0, "fields": {}}
        for doc_type in selected
    }
    tp = fp = fn = 0
    mismatches: list[str] = []

    for index in range(1, last + 1):
        case_name = f"przyklad_{index:02d}"
        case = dane / case_name
        for doc_type in selected:
            pdf = case / _PDF[doc_type]
            expected = json.loads((case / f"{doc_type}.json").read_text(encoding="utf-8"))
            processed = process_file(pdf, mode="bielik")
            got = processed.data if processed.document_type == doc_type else {}
            print(f"{case_name} {doc_type}", flush=True)
            bucket = stats[doc_type]
            bucket["n"] += 1
            for template, concrete, expected_value, got_value in _pairs(expected, got):
                field = bucket["fields"].setdefault(template, {"hit": 0, "n": 0})
                field["n"] += 1
                match = _same(expected_value, got_value)
                if match:
                    field["hit"] += 1
                else:
                    mismatches.append(
                        f"{case_name} {doc_type} {concrete}\n"
                        f"  expected: {expected_value!r}\n"
                        f"  got:      {got_value!r}"
                    )
                tp, fp, fn = _accumulate(tp, fp, fn, expected_value, got_value, match)

    for doc_type in selected:
        bucket = stats[doc_type]
        print(f"\n{doc_type}  cases={bucket['n']}")
        for template, field in bucket["fields"].items():
            pct = 100.0 * field["hit"] / field["n"] if field["n"] else 0.0
            print(f"  {template}: {field['hit']}/{field['n']} = {pct:.1f}%")

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    micro = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    print(f"\nmicro-F1 {micro:.3f}  (tp={tp} fp={fp} fn={fn})")
    print(f"mismatches: {len(mismatches)}")
    for line in mismatches[:15]:
        print(line)
    return 0


def _pairs(expected: object, got: object):
    expected_leaves = dict(_leaves(expected))
    got_leaves = dict(_leaves(got))
    paths = list(expected_leaves) + [path for path in got_leaves if path not in expected_leaves]
    for concrete in paths:
        template = re.sub(r"\[\d+\]", "[]", concrete)
        yield template, concrete, expected_leaves.get(concrete), got_leaves.get(concrete)


def _leaves(value: object, prefix: str = ""):
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            yield from _leaves(item, path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _leaves(item, f"{prefix}[{index}]")
    elif prefix:
        yield prefix, value


def _same(expected: object, got: object) -> bool:
    if expected is None or got is None:
        return expected is got
    if isinstance(expected, (int, float)) and isinstance(got, (int, float)):
        return float(expected) == float(got)
    return expected == got


def _accumulate(
    tp: int,
    fp: int,
    fn: int,
    expected: object,
    got: object,
    match: bool,
) -> tuple[int, int, int]:
    if match and expected is not None:
        return tp + 1, fp, fn
    if not match and expected is not None:
        fn += 1
    if not match and got is not None:
        fp += 1
    return tp, fp, fn


if __name__ == "__main__":
    raise SystemExit(main())

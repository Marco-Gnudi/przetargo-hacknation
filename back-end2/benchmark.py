"""Compare predictions with the paired reference JSON files.

Score definition:
- A leaf is counted only when the reference or the prediction is non-null.
- True positive: both non-null and equal.
- False positive: prediction is non-null and differs from the reference.
- False negative: reference is non-null and the prediction misses it.
- Null/null leaves are ignored.
- Numbers match within 0.001. Everything else is compared as text.
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from pipeline import load_rules, process_pdf

PAIRS = {
    "odwolanie.pdf": "odwolanie.json",
    "pelnomocnictwo.pdf": "pelnomocnictwo.json",
    "potwierdzenie_przelewu.pdf": "przelew.json",
}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Score extraction against reference JSON.")
    parser.add_argument("--data", default="../UZP-hacknation-task/dane", help="Organizer dane directory.")
    parser.add_argument("--report", default="reports/benchmark.md", help="Markdown report path.")
    args = parser.parse_args(argv)
    data = Path(args.data)
    report_path = Path(args.report)
    rules = load_rules()
    rows = []
    for pdf, reference in _cases(data):
        payload, diagnostic = process_pdf(pdf, rules)
        gold = _load_reference(reference) if reference else {}
        rows.append((pdf, diagnostic["document_type"], payload, gold))
    report = render_report(rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(report.split("## Fields with the most errors")[0].strip())
    print(f"Report written to {report_path}")
    return 0


def _cases(data):
    cases = []
    for pdf in sorted(data.rglob("*.pdf")):
        # Scans have their own references and are scored by backend/scripts/evaluate.py.
        if "skany" in pdf.parts:
            continue
        reference_name = PAIRS.get(pdf.name)
        reference = pdf.with_name(reference_name) if reference_name else None
        if reference is not None and not reference.exists():
            reference = None
        if reference is None and pdf.parent.name != "negatywne" and pdf.name not in PAIRS:
            reference = None
        cases.append((pdf, reference if reference and reference.exists() else (None if pdf.name in PAIRS else "EMPTY")))
    return cases


def _load_reference(reference):
    if reference == "EMPTY" or reference is None:
        return {}
    return json.loads(Path(reference).read_text(encoding="utf-8"))


def flatten(value, prefix=""):
    if isinstance(value, dict):
        items = {}
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else key
            items.update(flatten(child, path))
        return items
    if isinstance(value, list):
        items = {}
        for index, child in enumerate(value):
            items.update(flatten(child, f"{prefix}[{index}]"))
        return items
    return {prefix: value}


def same(left, right):
    if left is None or right is None:
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) < 0.001
    return str(left).strip() == str(right).strip()


def score_pair(predicted, gold):
    pred = flatten(predicted)
    truth = flatten(gold)
    paths = sorted(set(pred) | set(truth))
    counts = {"tp": 0, "fp": 0, "fn": 0}
    fields = []
    for path in paths:
        left = pred.get(path)
        right = truth.get(path)
        if left is None and right is None:
            continue
        if same(left, right):
            kind = "tp"
        elif left is None:
            kind = "fn"
        elif right is None:
            kind = "fp"
        else:
            kind = "fp"
            counts["fn"] += 1
        counts[kind] += 1
        fields.append((path, kind, left, right))
    return counts, fields


def f1(counts):
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    score = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, score


def render_report(rows):
    by_type = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    by_field = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    mistakes = []
    for pdf, document_type, predicted, gold in rows:
        counts, fields = score_pair(predicted, gold)
        group = document_type if gold else "empty"
        for key in ("tp", "fp", "fn"):
            by_type[group][key] += counts[key]
        for path, kind, left, right in fields:
            leaf = re.sub(r"\[\d+\]", "[]", path)
            by_field[f"{group}:{leaf}"][kind] += 1
            if kind != "tp":
                mistakes.append((pdf.name, path, left, right))
    lines = ["# Extraction benchmark", "", "Null leaves are ignored. A wrong non-null value counts as one false positive and one false negative.", ""]
    lines.append("## By document type")
    lines.append("")
    lines.append("| Type | Precision | Recall | F1 | TP | FP | FN |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for name, counts in sorted(by_type.items()):
        precision, recall, score = f1(counts)
        lines.append(f"| {name} | {precision:.3f} | {recall:.3f} | {score:.3f} | {counts['tp']} | {counts['fp']} | {counts['fn']} |")
    lines.append("")
    lines.append("## Fields with the most errors")
    lines.append("")
    ranked = sorted(by_field.items(), key=lambda item: item[1]["fp"] + item[1]["fn"], reverse=True)
    lines.append("| Field | FP | FN | TP |")
    lines.append("|---|---:|---:|---:|")
    for name, counts in ranked[:20]:
        if counts["fp"] + counts["fn"] == 0:
            continue
        lines.append(f"| {name} | {counts['fp']} | {counts['fn']} | {counts['tp']} |")
    lines.append("")
    lines.append("## Sample mismatches")
    lines.append("")
    for name, path, left, right in mistakes[:30]:
        lines.append(f"- `{name}` `{path}`: predicted `{left}` / reference `{right}`")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

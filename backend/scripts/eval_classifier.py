"""Score the text classifier on dane/, including negatives and decoys.

Ground truth uses the canonical training filenames. The classifier itself
never sees the filename. Run from backend/: python scripts/eval_classifier.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from odwolania.classifier import classify_text
from odwolania.config import task_data_dir
from odwolania.pdf_reader import read_pdf

_CANONICAL = {
    "odwolanie.pdf": "odwolanie",
    "pelnomocnictwo.pdf": "pelnomocnictwo",
    "potwierdzenie_przelewu.pdf": "przelew",
}


def expected_label(pdf: Path) -> str | None:
    return _CANONICAL.get(pdf.name)


def main() -> int:
    dane = task_data_dir() / "dane"
    pdfs = sorted(dane.rglob("*.pdf"))
    misses: list[str] = []
    correct = 0
    per_class: dict[str, list[int]] = {}

    for pdf in pdfs:
        expected = expected_label(pdf)
        result = classify_text(read_pdf(pdf))
        key = expected or "none"
        bucket = per_class.setdefault(key, [0, 0])
        bucket[1] += 1
        if result.label == expected:
            correct += 1
            bucket[0] += 1
            continue
        rel = pdf.relative_to(dane).as_posix()
        scores = ", ".join(f"{name}={score:g}" for name, score in result.scores.items())
        misses.append(f"{rel}  expected={expected}  predicted={result.label}  [{scores}]")

    total = len(pdfs)
    pct = 100.0 * correct / total if total else 0.0
    print(f"accuracy {correct}/{total} = {pct:.1f}%")
    for name in ("odwolanie", "pelnomocnictwo", "przelew", "none"):
        hit, count = per_class.get(name, (0, 0))
        print(f"  {name}: {hit}/{count}")
    print(f"misclassified: {len(misses)}")
    for line in misses:
        print(line)
    return 0 if not misses else 1


if __name__ == "__main__":
    raise SystemExit(main())

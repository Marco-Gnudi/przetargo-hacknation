"""Score the text classifier on dane/, including negatives and decoys.

Ground truth uses the canonical training filenames. The classifier itself
never sees the filename. Identical PDF bytes are also scored once, because
several decoys are copies of files in negatywne/. Run from backend/:
python scripts/eval_classifier.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from odwolania.classifier import classify_text
from odwolania.config import load_settings, task_data_dir
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
    threshold = load_settings().threshold
    misses: list[str] = []
    correct = 0
    unique_correct = 0
    seen_bytes: set[str] = set()
    empty = 0
    per_class: dict[str, list[int]] = {}
    closest: tuple[float, str, dict[str, float]] | None = None

    for pdf in pdfs:
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        first_copy = digest not in seen_bytes
        seen_bytes.add(digest)
        text = read_pdf(pdf)
        if not text.strip():
            empty += 1
        expected = expected_label(pdf)
        result = classify_text(text)
        key = expected or "none"
        bucket = per_class.setdefault(key, [0, 0])
        bucket[1] += 1
        ok = result.label == expected
        if ok:
            correct += 1
            bucket[0] += 1
            if first_copy:
                unique_correct += 1
        else:
            rel = pdf.relative_to(dane).as_posix()
            scores = ", ".join(f"{name}={score:g}" for name, score in result.scores.items())
            misses.append(f"{rel}  expected={expected}  predicted={result.label}  [{scores}]")
        if result.label is None:
            best = max(result.scores.values(), default=0.0)
            rel = pdf.relative_to(dane).as_posix()
            if closest is None or best > closest[0]:
                closest = (best, rel, result.scores)

    total = len(pdfs)
    unique = len(seen_bytes)
    pct = 100.0 * correct / total if total else 0.0
    print(f"accuracy {correct}/{total} = {pct:.1f}%")
    print(f"unique files {unique_correct}/{unique} = {100.0 * unique_correct / unique if unique else 0:.1f}%")
    print(f"empty text {empty} (no text layer; rejected before keywords)")
    for name in ("odwolanie", "pelnomocnictwo", "przelew", "none"):
        hit, count = per_class.get(name, (0, 0))
        print(f"  {name}: {hit}/{count}")
    if closest is not None:
        best, rel, scores = closest
        rendered = ", ".join(f"{name}={score:g}" for name, score in scores.items())
        print(f"highest score still rejected: {best:g} < threshold {threshold:g}  {rel}  [{rendered}]")
    print(f"misclassified: {len(misses)}")
    for line in misses:
        print(line)
    return 0 if not misses else 1


if __name__ == "__main__":
    raise SystemExit(main())

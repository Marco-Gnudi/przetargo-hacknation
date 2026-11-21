"""OCR every PDF under a folder in parallel so evaluate.py reads from the cache.

    python backend/scripts/warm_ocr.py /tmp/synth --workers 4
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "back-end2"))
# Tesseract's own OpenMP threads thrash when several processes run at once.
os.environ["OMP_THREAD_LIMIT"] = "1"


def _read(path: str) -> str:
    from pdf_reader import read_pdf

    return read_pdf(path).text_source


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    pdfs = [str(path) for path in sorted(args.folder.rglob("*.pdf"))]
    with ProcessPoolExecutor(args.workers) as pool:
        sources = list(pool.map(_read, pdfs))
    print(f"{len(pdfs)} PDFs, {sources.count('ocr')} through OCR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

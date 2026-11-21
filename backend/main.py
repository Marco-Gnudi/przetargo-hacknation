"""CLI: python main.py --input <dir> --output <dir>."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from odwolania.pipeline import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Turn KIO appeal PDFs into JSON.")
    parser.add_argument("--input", required=True, type=Path, help="Folder of case subfolders")
    parser.add_argument("--output", required=True, type=Path, help="Where JSON files are written")
    args = parser.parse_args(argv)

    input_dir = args.input
    output_dir = args.output
    if not input_dir.is_dir():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        return 2

    written = run(input_dir, output_dir)
    for path in written:
        print(path)
    print(f"Wrote {len(written)} JSON file(s) to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

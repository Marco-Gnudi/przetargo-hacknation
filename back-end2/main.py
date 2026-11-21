"""Process one PDF, one case folder, or a directory tree.

Examples:
  python main.py ../UZP-hacknation-task/dane/przyklad_01/odwolanie.pdf
  python main.py ../UZP-hacknation-task/dane/przyklad_01 --output output
  python main.py --input ../UZP-hacknation-task/dane --output output
"""

import argparse
import json
import sys
import traceback
from pathlib import Path

from pipeline import load_rules, process_pdf


def main(argv=None):
    parser = argparse.ArgumentParser(description="Deterministic PDF to JSON extraction.")
    parser.add_argument("path", nargs="?", help="PDF file or directory.")
    parser.add_argument("--input", dest="input_dir", help="Directory of PDFs. Overrides path.")
    parser.add_argument("--output", default="output", help="Directory for JSON results.")
    parser.add_argument("--rules", help="Alternate rules JSON.")
    args = parser.parse_args(argv)

    source = Path(args.input_dir or args.path or "input")
    if not source.exists():
        print(f"Input not found: {source}", file=sys.stderr)
        return 2
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    log_path = output_root / "_logs" / "processing.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    rules = load_rules(args.rules)
    root = source if source.is_dir() else source.parent
    pdfs = sorted(source.rglob("*.pdf")) if source.is_dir() else [source]

    ok = 0
    failed = 0
    with log_path.open("w", encoding="utf-8") as log:
        for pdf in pdfs:
            try:
                payload, diagnostic = process_pdf(pdf, rules)
                relative = _relative(pdf, root)
                destination = output_root / relative.with_suffix(".json")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                diagnostic["output"] = str(destination)
                if diagnostic["warnings"]:
                    log.write(json.dumps(diagnostic, ensure_ascii=False) + "\n")
                ok += 1
            except Exception:
                failed += 1
                log.write(json.dumps({
                    "file": str(pdf),
                    "error": traceback.format_exc(),
                }, ensure_ascii=False) + "\n")
    print(f"Processed {ok} PDF(s), {failed} failure(s). JSON is in {output_root}.")
    return 0 if ok or not pdfs else 1


def _relative(pdf, root):
    try:
        return pdf.relative_to(root)
    except ValueError:
        return Path(pdf.name)


if __name__ == "__main__":
    raise SystemExit(main())

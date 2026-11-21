"""Send one transfer PDF to Bielik and print the JSON beside the expected file.

Run from backend/:  python scripts/smoke_llm.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from odwolania.config import task_data_dir
from odwolania.llm import LLMClient
from odwolania.pdf_reader import read_pdf


def main() -> int:
    data = task_data_dir()
    pdf_path = data / "dane" / "przyklad_01" / "potwierdzenie_przelewu.pdf"
    schema_path = data / "oczekiwane-json" / "przelew.json"
    expected_path = data / "dane" / "przyklad_01" / "przelew.json"

    text = read_pdf(pdf_path)
    schema = schema_path.read_text(encoding="utf-8")
    prompt = (
        "Wyodrębnij z potwierdzenia przelewu pola dokumentu przelew. "
        "Zwróć jeden obiekt JSON o tej strukturze (null, gdy pola nie ma w tekście):\n"
        f"{schema}"
    )
    result = LLMClient().extract_json(prompt, text)
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    print("=== model ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=== expected przyklad_01/przelew.json ===")
    print(json.dumps(expected, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

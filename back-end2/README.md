# back-end2

Deterministic PDF to JSON extractor for PrzetarGO. It does not call a language model.

The organizer asks for Python 3.13+. The modules use the standard library plus PyMuPDF and also run on Python 3.12.

## Run

```bash
cd back-end2
python3 -m pip install -r requirements.txt
python3 main.py --input ../UZP-hacknation-task/dane --output output
python3 benchmark.py --data ../UZP-hacknation-task/dane
python3 -m unittest discover -s tests
```

`main.py` accepts one PDF, one case folder, or a directory tree. JSON keeps the input's relative folders and the PDF basename (`odwolanie.pdf` becomes `odwolanie.json`). Files that are not an appeal, a power of attorney, or a transfer confirmation become `{}`. Failures are recorded in `output/_logs/processing.jsonl` and do not stop the batch.

Drop files in `input/` and run `python3 main.py` to use the default folders.

## Add a document class

1. Add its keywords and heading to `configs/rules.json`.
2. If labeled fields are enough, extend the label list in that file and reuse `extractors/przelew.py` as the pattern.
3. If the document needs sections, add `extractors/<type>.py` and register it in `extractors/__init__.py`.
4. Add the required keys in `validators.py`.

Do not put example company names or account numbers in the rules.

## Current coverage

On the 180 paired reference files, leaf-level F1 is about 0.96 for appeals, 0.88 for powers of attorney, and 0.96 for transfers. The 16 documents that should stay unclassified produce `{}`. The full table is `reports/benchmark.md`.

The weakest fields are power-of-attorney signatories and a few contracting-authority names when the party block runs into the next paragraph.

## Limits

Training PDFs have a text layer. A scanned file is reported as needing OCR. Tesseract is used only when it is already installed, and it is not required.

`czynnosc_powod_id` is taken from the sentence before the first `Zarzut nr 1`. Id 6 uses the wording stored in the reference files (`Odpowiedzi i wyjaśnienia do SWZ`). The schema comment writes that label with a slash.

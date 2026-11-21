# back-end2

Deterministic PDF to JSON extractor for PrzetarGO. It does not call a language model.

The organizer asks for Python 3.13+. The modules use the standard library plus PyMuPDF and also run on Python 3.12.

## Open the website

On macOS, with Python 3.13 installed:

```bash
cd back-end2
./start.sh
```

Then open http://127.0.0.1:8000/. The same process serves the existing frontend and the extractor. Upload one or more PDFs and press **Przetwórz dokumenty**.

`start.sh` creates `.venv` with `python3.13` if needed and installs `requirements.txt`. If the `python3.13` command has another name, run `PYTHON=/path/to/python3.13 ./start.sh`.

The CLI is unchanged and remains the entry point for batch evaluation:

```bash
python3 main.py --input ../UZP-hacknation-task/dane --output output
```

## Run the CLI

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

Training PDFs have a text layer. A page with fewer than 50 characters of text is sent through Tesseract (`pol` language data; `osd` for page orientation). A digital PDF with a few scanned pages has only those pages OCR'd. Sideways or upside-down scans are turned upright before OCR. Without Tesseract installed, a scanned file is reported as needing OCR.

`OCR_TESSDATA` in `backend/.env` can point at another folder with `pol.traineddata`, such as `tessdata_best`. On our scans it did not beat the system model, so it is off by default.

To check OCR on files the rules were not tuned on, `backend/scripts/make_synthetic_scans.py` turns the text examples into degraded scans with their reference JSONs, and `backend/scripts/warm_ocr.py` OCRs a folder in parallel before `backend/scripts/evaluate.py` scores it.

`czynnosc_powod_id` is taken from the sentence before the first `Zarzut nr 1`. Id 6 uses the wording stored in the reference files (`Odpowiedzi i wyjaśnienia do SWZ`). The schema comment writes that label with a slash.

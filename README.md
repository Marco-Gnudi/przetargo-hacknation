# PrzetarGO (przetargo-hacknation)

Team project for HackNation 2026 in Bydgoszcz (21-22 Nov 2026).

**Team:** Marco Gnudi, Wiktor

## The challenge
_To be filled in once the challenge is announced._

## How we work
- `main` must always be demo-ready.
- Work on a short-lived branch: `feat/<thing>`, `fix/<thing>`.
- Commit small and often with clear messages.
- Merge into `main` via a small pull request; pull `main` often.

```bash
git checkout main && git pull
git checkout -b feat/my-feature
# ...work...
git add -A && git commit -m "Add my feature"
git push -u origin feat/my-feature
gh pr create --fill
```

## For UZP Judges — Quick Start

PrzetarGO reads KIO appeal case PDFs (odwołanie, pełnomocnictwo, potwierdzenie przelewu) and writes one JSON file per PDF in the official schema. Everything runs on your own computer: the web page and the batch command use the same extraction engine, and documents never leave the machine unless you turn on Mistral mode.

### What you need

- Python 3.13 or newer.
- Tesseract OCR 5.x with Polish (`pol`) and English (`eng`) data, for scanned PDFs. Text PDFs work without it; see [Tesseract](#tesseract-for-scanned-pdfs).
- About 1 GB free disk, 16 GB RAM is plenty, no GPU.
- Optional: a Mistral API key, only for hybrid mode.

### Get the code

```bash
git clone https://github.com/Marco-Gnudi/przetargo-hacknation.git
cd przetargo-hacknation
```

Or download the ZIP from GitHub (**Code → Download ZIP**) and unpack it.

### Start the website (one command)

macOS / Linux:

```bash
./start.sh
```

Windows (double-click or run in `cmd`):

```bat
start.bat
```

The first run creates `.venv`, installs `requirements.txt` (about a minute) and checks your setup. Then open **http://127.0.0.1:8000/**. The server listens only on this computer (`127.0.0.1`). Press Ctrl+C to stop it. Use another port with `PORT=8010 ./start.sh` (Windows: `set PORT=8010` then `start.bat`).

On the page:

1. Choose **Regularne / Regular** (deterministic, no key) or **Mistral** (rules first, then the model fills gaps).
2. For Mistral, paste the key and press **Sprawdź połączenie / Check connection**. The key stays in the tab's memory only: it is not saved in the browser, on disk or in logs, and it is sent only to the local server, which passes it to the model API.
3. Add up to **150 PDFs** (drag and drop or click), or pick an example case. The page uploads them 10 at a time and shows the progress.
4. Press **Przetwórz dokumenty / Process documents**. Each document shows its type, fields and missing values; you can copy or download its JSON. All files from one run are also saved as `input/caseN/*.pdf` and `output/caseN/*.json`.

### Run the full batch (no interaction)

Put the PDFs in `input/` (any folder depth), then:

```bash
./start.sh batch          # Windows: start.bat batch
```

or, with the virtual environment already set up:

```bash
.venv/bin/python main.py --input input --output output        # Windows: .venv\Scripts\python main.py
```

`input/case1/document.pdf` becomes `output/case1/document.json`. Documents are classified by content, not by file name. A document that is not one of the three types is written as `{}`. A per-file log with status, timing and warnings goes to `output/_logs/processing.jsonl`, and the summary at the end lists any file that could not be read. Options: `--mode auto|deterministic|hybrid|llm-only` (default `auto`: hybrid when a key is set, otherwise deterministic) and `--workers N` (default 4).

### Speed: 150 documents in 45 minutes

Measured on a 4-core cloud VM without a GPU, deterministic mode, OCR cache cleared:

| Run | Files | Scans | Time |
| --- | --- | --- | --- |
| `main.py`, whole organizer dataset | 226 | 33 | 60 s |
| Web page flow, 150 random files in batches of 10 | 150 | 20 | 112 s |

A text PDF takes under 0.2 s, a scanned transfer confirmation about 1.5 s and a scanned appeal about 10 s of OCR. Hybrid mode adds Mistral requests only for fields the rules left empty and for weak scans; it was not timed because we had no key during testing. Even at several seconds per request, 150 documents stay well within 45 minutes. At Scaleway list prices (€0.15 per million input tokens, €0.35 per million output tokens) a 150-document run costs well under €1; this is an estimate, not a measurement.

### Deterministic mode (default)

Rules plus PyMuPDF/pdfplumber for text PDFs and Tesseract for scans. It needs no key, no network and no GPU, and every component is open source.

### Mistral mode (optional)

Set the key for the batch command, or paste it in the page:

```bash
export MISTRAL_API_KEY=...            # Windows cmd: set MISTRAL_API_KEY=...   PowerShell: $env:MISTRAL_API_KEY="..."
./start.sh batch
```

`LLM_API_KEY` works too, and both can live in `backend/.env` (see `backend/.env.example`; never commit it). Before a batch, `main.py` makes one test request. If the key is missing or rejected, `--mode hybrid` stops with a clear message and `--mode auto` continues in deterministic mode and says so. The summary and the page report how many Mistral requests were made and how many failed. When a request fails, the field keeps the deterministic value or `null`; nothing is invented.

| | Default | Alternative |
| --- | --- | --- |
| Model | Mistral Small 3.2 24B Instruct (`mistral-small-3.2-24b-instruct-2506`) | Mistral Small 4 (`mistral-small-2603`) |
| License | Apache 2.0, open weights | Apache 2.0, open weights |
| API | Scaleway Generative APIs, `https://api.scaleway.ai/v1` | Mistral EU, `https://api.eu.mistral.ai/v1` |
| Processing location | Paris, France (EU) | EU/EFTA |

Use the alternative with `MISTRAL_BASE_URL=https://api.eu.mistral.ai/v1 MISTRAL_MODEL=mistral-small-2603`. We could not test it without a key. The model is a general-purpose LLM (text, and page images for weak scans); PrzetarGO does not use the proprietary Mistral OCR API.

### Tesseract for scanned PDFs

- **macOS:** `brew install tesseract tesseract-lang`
- **Ubuntu/Debian:** `sudo apt install tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng`
- **Windows:** install Tesseract 5.x from https://github.com/UB-Mannheim/tesseract/wiki and tick Polish under *Additional language data*. Add `C:\Program Files\Tesseract-OCR` to PATH, or set `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`. If Polish is missing, copy `pol.traineddata` from https://github.com/tesseract-ocr/tessdata_fast into `C:\Program Files\Tesseract-OCR\tessdata`.

PrzetarGO finds Tesseract on PATH, in the usual install folders, or via `TESSERACT_CMD`. Without it, text PDFs still work and scans are reported as **needs OCR** and written as `{}`; they are never guessed.

### Check your setup

```bash
./start.sh doctor                     # Windows: start.bat doctor
.venv/bin/python doctor.py --check-llm   # also tests the Mistral key (one tiny request)
```

It prints PASS / FAIL / SKIP for Python, packages, Tesseract, `pol`/`eng` data, a real OCR test, folder permissions, the port, and the Mistral endpoint, model and key (the key is never printed).

### Docker (optional, includes Tesseract)

```bash
docker build -t przetargo .
docker run --rm -p 127.0.0.1:8000:8000 -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" przetargo
docker run --rm -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" -e MISTRAL_API_KEY przetargo python main.py
```

On Linux add `--user "$(id -u):$(id -g)"` so the output files belong to you.

### Troubleshooting

| Problem | Fix |
| --- | --- |
| "PrzetarGO needs Python 3.13 or newer" | Install 3.13 (macOS `brew install python@3.13`, Ubuntu `sudo apt install python3.13 python3.13-venv`, Windows `winget install -e --id Python.Python.3.13`), or point to it with `PYTHON=/path/to/python3.13 ./start.sh`. If `.venv` was made with an older Python, delete `.venv` and start again. |
| Tesseract not found | Install it (above) or set `TESSERACT_CMD`. Run `./start.sh doctor`. |
| Polish data (`pol`) missing | Ubuntu: `sudo apt install tesseract-ocr-pol`; macOS: `brew install tesseract-lang`; Windows: copy `pol.traineddata` into `tessdata`. |
| Mistral key rejected (HTTP 401/403) | Check the key, and that the model name exists at that endpoint. `doctor.py --check-llm` shows the HTTP status. |
| EU endpoint unreachable or model missing | Go back to the default: unset `MISTRAL_BASE_URL` and `MISTRAL_MODEL` (Scaleway, Paris). Or run deterministic mode. |
| Port 8000 in use | `PORT=8010 ./start.sh` (Windows: `set PORT=8010`). |
| Missing Python packages | Delete `.venv` and run the start script again, or `.venv/bin/python -m pip install -r requirements.txt`. |
| A scan shows "needs OCR" | Tesseract is missing or could not read the page; run `./start.sh doctor`. |

### Developers

Tests: `cd back-end2 && ../.venv/bin/python -m pytest` and `cd backend && ../.venv/bin/python -m pytest` (install `pytest` and `httpx` into `.venv` first). Score against the reference JSON: `cd back-end2 && ../.venv/bin/python benchmark.py`.

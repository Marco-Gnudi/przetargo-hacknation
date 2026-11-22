# PrzetarGO (przetargo-hacknation)

Team project for HackNation 2026 in Bydgoszcz (21-22 Nov 2026).

**Team:** Marco Gnudi, Wiktor

## The challenge

Odwołania2JSON, for the Public Procurement Office (UZP): read the PDFs in a KIO appeal case and write one JSON file per document in the official schema.

## Quick Start

PrzetarGO reads KIO appeal PDFs and writes one JSON file per PDF. It runs on your computer. A downloaded ZIP works the same way as a git clone; Git is not required.

macOS / Linux:

```bash
git clone https://github.com/Marco-Gnudi/przetargo-hacknation.git
cd przetargo-hacknation
./start.sh
```

Windows, in Command Prompt:

```bat
git clone https://github.com/Marco-Gnudi/przetargo-hacknation.git
cd przetargo-hacknation
start.bat
```

The script creates `.venv`, installs the Python packages, and prints **http://127.0.0.1:8000/**. It opens that address when the page is ready. Leave the terminal open; Ctrl+C stops the server. Another port: `PORT=8010 ./start.sh` (Windows: `set PORT=8010` then `start.bat`).

You need **Python 3.13 or newer** before the first run. If it is missing, the script prints the install command for your system and stops. It does not install Python for you.

**Tesseract OCR 5 with Polish data** is needed only for scans. If it is missing, the script offers to install it (Homebrew, apt, or winget) and asks before doing so. apt and winget may ask for an administrator password, because Tesseract is a system program. Saying no is fine: text PDFs still run, and scans are reported instead of guessed. English OCR data is not used.

Put each case in its own folder under `input/`, then press **Przetwórz dokumenty**. Results land in `output/` under the same names:

```
input/case1/odwolanie.pdf   ->   output/case1/odwolanie.json
```

The page processes every PDF under `input/`. A file that is not an appeal, a power of attorney, or a transfer confirmation is written as `{}`. Classification uses the document text, not the file name. No API key is required for that. For Mistral, paste the key into **Klucz API Mistral** and press **Dodaj**. The key stays in that browser tab only.

Check the machine without starting the server: `./start.sh doctor` (Windows: `start.bat doctor`).

## Setup in detail

### Python packages the script installs

Only when `.venv` is missing or `requirements.txt` has changed:

| Package | What it is for |
| --- | --- |
| pymupdf, pypdf, pdfplumber | Reading the PDFs |
| pytesseract, pillow | Sending scanned pages to Tesseract |
| PyYAML, python-dotenv | Settings |
| openai | The Mistral API client |
| fastapi, uvicorn, python-multipart | The website |

### Python 3.13

- macOS: `brew install python@3.13`
- Ubuntu/Debian: `sudo apt-get install python3.13 python3.13-venv` (add `ppa:deadsnakes/ppa` first if 3.13 is not in the release)
- Windows: `winget install -e --id Python.Python.3.13` or https://www.python.org/downloads/ (tick "Add python.exe to PATH")
- An existing install: `PYTHON=/path/to/python3.13 ./start.sh` (Windows: `set PYTHON=C:\Path\to\python.exe`)

### Tesseract for scanned PDFs

OCR calls Tesseract with the Polish (`pol`) language data only. English (`eng`) is optional and is not used. A custom `TESSERACT_CMD` in the environment or in `backend/.env` is used as-is.

- **macOS:** `brew install tesseract tesseract-lang`
- **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr tesseract-ocr-pol`
- **Windows:** Tesseract 5 from https://github.com/UB-Mannheim/tesseract/wiki (tick Polish), or `winget install -e --id UB-Mannheim.TesseractOCR`. If Polish was not included, copy `pol.traineddata` from https://github.com/tesseract-ocr/tessdata_fast into the `tessdata` folder next to `tesseract.exe`. If the program is not on PATH, set `TESSERACT_CMD` in `backend/.env`.

Without Tesseract, text PDFs still work. A scan is reported as needing OCR and written as `{}`.

`./start.sh doctor` prints PASS, WARN or SKIP for Python, packages, Tesseract, Polish data, a real OCR test, the folders, the port, and the Mistral endpoint. English data is reported as optional. A missing Mistral key is SKIP: deterministic processing still runs, and the key can be pasted in the page. The key is never printed. About 1 GB of disk is enough. No GPU is required.

### Input and output

```
input/case1/odwolanie_nr_1.pdf          ->  output/case1/odwolanie_nr_1.json
input/case1/pelnomocnictwo_nr_1.pdf     ->  output/case1/pelnomocnictwo_nr_1.json
input/case2/przelew_nr_1.pdf            ->  output/case2/przelew_nr_1.json
```

A folder name can be letters, digits, dots, underscores and hyphens. The summary lists each document as it finishes, then the time, the Mistral token count when a key was used, how many documents were recognised, and how many were out of scope.

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

A text PDF takes under 0.2 s, a scanned transfer confirmation about 1.5 s and a scanned appeal about 10 s of OCR. Mistral-only mode, which is what the Hacknation Task page runs, took 55 seconds and about 144,000 tokens for 20 official cases (63 PDFs) on the same machine. At Scaleway list prices (€0.15 per million input tokens, €0.35 per million output tokens) a 150-document run costs well under €1.

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

### Check your setup

```bash
./start.sh doctor                     # Windows: start.bat doctor
.venv/bin/python doctor.py --check-llm   # also tests the Mistral key (one tiny request)
```

It prints PASS, WARN or SKIP. WARN means text PDFs still run. The Mistral key is never printed.

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
| Polish data (`pol`) missing | Ubuntu: `sudo apt-get install tesseract-ocr-pol`; macOS: `brew install tesseract-lang`; Windows: copy `pol.traineddata` into `tessdata`. English data is not required. |
| Mistral key rejected (HTTP 401/403) | Check the key, and that the model name exists at that endpoint. `doctor.py --check-llm` shows the HTTP status. |
| EU endpoint unreachable or model missing | Go back to the default: unset `MISTRAL_BASE_URL` and `MISTRAL_MODEL` (Scaleway, Paris). Or run deterministic mode. |
| Port 8000 in use | `PORT=8010 ./start.sh` (Windows: `set PORT=8010`). |
| Missing Python packages | Delete `.venv` and run the start script again, or `.venv/bin/python -m pip install -r requirements.txt`. |
| A scan shows "needs OCR" | Tesseract is missing or could not read the page; run `./start.sh doctor`. |

### How we work

- `main` must always be demo-ready.
- Work on a short-lived branch: `feat/<thing>`, `fix/<thing>`.
- Commit small and often with clear messages.
- Merge into `main` via a small pull request; pull `main` often.

### Developers

Tests: `cd back-end2 && ../.venv/bin/python -m pytest` and `cd backend && ../.venv/bin/python -m pytest` (install `pytest` and `httpx` into `.venv` first). Score against the reference JSON: `cd back-end2 && ../.venv/bin/python benchmark.py`. The pitch slide is `docs/slides/f1_overview.png`; `python scripts/make_f1_chart.py` redraws it from `reports/stats.json`.

# Odwołania2JSON backend

Classify KIO appeal PDFs and write JSON. The CLI, PDF reader, rules, and Bielik client are wired. The HTTP API serves the PrzetarGO front-end.

Training data lives at the repo root in `UZP-hacknation-task/` (the brief calls this folder `data/`). Paths inside the package are resolved from the repo root, not the shell's current directory.

## Setup

From `backend/`:

```bat
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`. Do not commit `.env`.

## Run

```bat
.venv\Scripts\python.exe main.py --input ..\UZP-hacknation-task\szablon-aplikacja\input --output output
```

Or, after the venv exists, `start.bat` with the same `--input` and `--output` arguments.

Each `<input>/<case>/*.pdf` is written to `<output>/<case>/<same name>.json`.

## Smoke test (calls Bielik)

```bat
.venv\Scripts\python.exe scripts\smoke_llm.py
```

Reads `przyklad_01/potwierdzenie_przelewu.pdf`, asks for the przelew fields, and prints the model JSON next to `przyklad_01/przelew.json`.

## Evaluate

```bat
.venv\Scripts\python.exe scripts\eval_classifier.py
.venv\Scripts\python.exe scripts\eval_przelew.py
```

The classifier is scored on `dane/`, including `negatywne/` and the decoy PDFs. The przelew eval compares all 60 cases with the expected `przelew.json` and reports whether each field came from a rule or the LLM.

## UI

From the repo root, `start_ui.bat` starts the API on http://127.0.0.1:8000 and the front-end on http://127.0.0.1:8080.

`POST /api/process` takes PDF files and `mode` (`regular` or `bielik`). `regular` uses rules only. `bielik` keeps the rules and asks the model only when classification or a przelew field is still empty. `GET /api/health` returns `{"status": "ok"}`.

## Tests

```bat
.venv\Scripts\python.exe -m pytest
```

Tests that call the LLM API must be marked `@pytest.mark.llm`. The default suite does not call the API.

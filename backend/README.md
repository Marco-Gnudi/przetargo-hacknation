# Odwołania2JSON backend

Classify KIO appeal PDFs and write JSON. Classification is still a stub, so every file currently becomes `{}`. The CLI, PDF reader, config and Bielik client are wired.

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

## Tests

```bat
.venv\Scripts\python.exe -m pytest
```

Tests that call the LLM API must be marked `@pytest.mark.llm`. The default suite does not call the API.

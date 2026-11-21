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

Each `<input>/<case>/*.pdf` is written to `<output>/<case>/<same name>.json`. The CLI fills `odwolanie` and `pelnomocnictwo` with Bielik. `przelew` stays on the rule extractor, with the model only for fields the rules leave empty.

## Smoke test (calls Bielik)

```bat
.venv\Scripts\python.exe scripts\smoke_llm.py
```

Reads `przyklad_01/potwierdzenie_przelewu.pdf`, asks for the przelew fields, and prints the model JSON next to `przyklad_01/przelew.json`.

## Evaluate

```bat
.venv\Scripts\python.exe scripts\eval_classifier.py
.venv\Scripts\python.exe scripts\eval_przelew.py
.venv\Scripts\python.exe scripts\eval_llm.py --limit 5
.venv\Scripts\python.exe scripts\eval_llm.py
```

The classifier is scored on `dane/`, including `negatywne/` and the decoy PDFs. The przelew eval compares all 60 cases with the expected `przelew.json` and reports whether each field came from a rule or the LLM. `eval_llm.py` scores `odwolanie` and `pelnomocnictwo` in bielik mode (`--type` limits the type, `--limit N` the first N cases). Model replies are stored in `backend/.cache/`, which is gitignored, so a rerun with the same prompt does not call Bielik again.

## UI

From the repo root, `start_ui.bat` starts the API on http://127.0.0.1:8000 and the front-end on http://127.0.0.1:8080.

`POST /api/process` takes PDF files and `mode` (`regular` or `bielik`). `regular` uses rules only. `bielik` keeps the rules for classification and for przelew, and asks Bielik for `odwolanie` and `pelnomocnictwo` (and for a przelew field or a type the rules leave empty). `GET /api/health` returns `{"status": "ok"}`.

## Tests

```bat
.venv\Scripts\python.exe -m pytest
```

Tests that call the LLM API must be marked `@pytest.mark.llm`. The default suite does not call the API.

#!/bin/sh
# Start the PrzetarGO site and the deterministic extractor on http://127.0.0.1:8000
set -eu
cd "$(dirname "$0")"

PY="${PYTHON:-python3.13}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Python 3.13 was not found. Install it, or run: PYTHON=/path/to/python3.13 $0" >&2
  exit 1
fi

if [ ! -x .venv/bin/python ] || ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  "$PY" -m venv .venv
fi

.venv/bin/python -m pip install -q -r requirements.txt
exec .venv/bin/python api.py

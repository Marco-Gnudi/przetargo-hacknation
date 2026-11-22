#!/bin/sh
# PrzetarGO for macOS and Linux.
#   ./start.sh               set up (first run only) and open the web page on http://127.0.0.1:8000
#   ./start.sh batch [args]  set up, then run the batch CLI: input/ -> output/ (see python main.py --help)
#   ./start.sh doctor        set up, then check Python, packages, Tesseract and the Mistral settings
set -eu
cd "$(dirname "$0")"

find_python() {
  for candidate in ${PYTHON:-} python3.14 python3.13 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
      "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)' 2>/dev/null; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

if [ ! -x .venv/bin/python ]; then
  if ! PY=$(find_python); then
    echo "PrzetarGO needs Python 3.13 or newer." >&2
    echo "  macOS:         brew install python@3.13" >&2
    echo "  Ubuntu/Debian: sudo apt install python3.13 python3.13-venv" >&2
    echo "Then run ./start.sh again, or point to it: PYTHON=/path/to/python3.13 ./start.sh" >&2
    exit 1
  fi
  echo "Creating .venv with $("$PY" --version)..."
  "$PY" -m venv .venv
fi

if ! .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)'; then
  echo ".venv uses $(.venv/bin/python --version); 3.13+ is required. Delete .venv and run ./start.sh again." >&2
  exit 1
fi

if ! cmp -s requirements.txt .venv/requirements.installed 2>/dev/null; then
  echo "Installing Python packages (first run takes a minute)..."
  .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
  cp requirements.txt .venv/requirements.installed
fi

command="${1:-web}"
case "$command" in
  batch)
    shift
    exec .venv/bin/python main.py "$@"
    ;;
  doctor)
    shift
    exec .venv/bin/python doctor.py "$@"
    ;;
  web)
    .venv/bin/python doctor.py --startup || exit 1
    echo
    echo "PrzetarGO is running at http://127.0.0.1:${PORT:-8000}/  (press Ctrl+C to stop)"
    HOST=127.0.0.1 exec .venv/bin/python back-end2/api.py
    ;;
  *)
    echo "Usage: ./start.sh [web|batch|doctor] [options]" >&2
    exit 2
    ;;
esac

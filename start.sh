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

python_missing() {
  echo "PrzetarGO needs Python 3.13 or newer, and it is not installed." >&2
  echo "Install it, then run ./start.sh again:" >&2
  echo "  macOS:         brew install python@3.13" >&2
  echo "  Ubuntu/Debian: sudo apt-get install python3.13 python3.13-venv" >&2
  echo "                 (if 3.13 is not in your Ubuntu release: sudo add-apt-repository ppa:deadsnakes/ppa)" >&2
  echo "  Any system:    https://www.python.org/downloads/" >&2
  echo "Or point at an existing install: PYTHON=/path/to/python3.13 ./start.sh" >&2
}

# TESSERACT_CMD from the environment wins, then backend/.env, then PATH.
tesseract_bin() {
  if [ -n "${TESSERACT_CMD:-}" ] && [ -x "${TESSERACT_CMD}" ]; then
    printf '%s\n' "$TESSERACT_CMD"
    return 0
  fi
  if [ -f backend/.env ]; then
    configured=$(grep -E '^[[:space:]]*TESSERACT_CMD=' backend/.env | tail -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' ')
    if [ -n "$configured" ] && [ -x "$configured" ]; then
      printf '%s\n' "$configured"
      return 0
    fi
  fi
  if command -v tesseract >/dev/null 2>&1; then
    command -v tesseract
    return 0
  fi
  for candidate in /opt/homebrew/bin/tesseract /usr/local/bin/tesseract /usr/bin/tesseract; do
    if [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

# OCR calls Tesseract with Polish only. English data is not used.
ocr_ready() {
  bin=$(tesseract_bin || true)
  [ -n "$bin" ] || return 1
  langs=$("$bin" --list-langs 2>/dev/null || true)
  printf '%s\n' "$langs" | grep -qx 'pol'
}

offer_tesseract() {
  if ocr_ready; then
    return 0
  fi
  echo "Tesseract OCR with Polish language data is not installed."
  echo "Text PDFs still work. Scanned PDFs need Tesseract; nothing is guessed when it is missing."
  if [ "$(uname -s)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    echo "Homebrew can install it for your user (no administrator password):"
    echo "  brew install tesseract tesseract-lang"
    if [ ! -t 0 ]; then
      echo "Non-interactive shell, so this step was skipped. Run that command, then ./start.sh again."
      return 0
    fi
    printf "Install Tesseract now? [y/N] "
    read -r answer
    case "$answer" in
      y|Y|yes|Yes)
        brew install tesseract tesseract-lang || echo "Install failed. Text PDFs will still run."
        ;;
      *)
        echo "Skipped. Text PDFs will run. Install later with: brew install tesseract tesseract-lang"
        ;;
    esac
  elif command -v apt-get >/dev/null 2>&1; then
    echo "apt can install it. sudo asks for your password because Tesseract is a system program, not a Python package."
    echo "  sudo apt-get install -y tesseract-ocr tesseract-ocr-pol"
    if [ ! -t 0 ]; then
      echo "Non-interactive shell, so this step was skipped. Run that command, then ./start.sh again."
      return 0
    fi
    printf "Install Tesseract now? [y/N] "
    read -r answer
    case "$answer" in
      y|Y|yes|Yes)
        sudo apt-get install -y tesseract-ocr tesseract-ocr-pol || echo "Install failed. Text PDFs will still run."
        ;;
      *)
        echo "Skipped. Text PDFs will run. Install later with: sudo apt-get install -y tesseract-ocr tesseract-ocr-pol"
        ;;
    esac
  else
    echo "No Homebrew or apt was found. Install Tesseract 5 with Polish data, then run ./start.sh again."
    echo "  macOS:         brew install tesseract tesseract-lang"
    echo "  Ubuntu/Debian: sudo apt-get install tesseract-ocr tesseract-ocr-pol"
  fi
}

open_browser() {
  if [ "${PRZETARGO_NO_BROWSER:-}" = "1" ]; then
    return 0
  fi
  url="http://127.0.0.1:${PORT:-8000}/"
  (
    i=0
    while [ "$i" -lt 40 ]; do
      if .venv/bin/python -c "import urllib.request; urllib.request.urlopen('${url}api/health', timeout=1)" >/dev/null 2>&1; then
        if [ "$(uname -s)" = "Darwin" ] && command -v open >/dev/null 2>&1; then
          open "$url" >/dev/null 2>&1 || true
        elif command -v xdg-open >/dev/null 2>&1; then
          xdg-open "$url" >/dev/null 2>&1 || true
        fi
        exit 0
      fi
      i=$((i + 1))
      sleep 0.25
    done
  ) >/dev/null 2>&1 &
}

if [ ! -x .venv/bin/python ]; then
  if ! PY=$(find_python); then
    python_missing
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

offer_tesseract

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
    echo "Put case folders in input/. JSON is written to output/."
    open_browser
    HOST=127.0.0.1 exec .venv/bin/python back-end2/api.py
    ;;
  *)
    echo "Usage: ./start.sh [web|batch|doctor] [options]" >&2
    exit 2
    ;;
esac

"""Check that this machine can run PrzetarGO. Prints PASS / FAIL / SKIP per item.

    python doctor.py              # everything except a live API call
    python doctor.py --check-llm  # also sends one tiny request with MISTRAL_API_KEY

Exit code 1 only when PrzetarGO cannot run at all (Python or packages). OCR problems are reported
but do not stop the app: text PDFs still work, scanned PDFs need Tesseract.
"""

from __future__ import annotations

import argparse
import importlib
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "back-end2"))
sys.path.insert(1, str(ROOT / "backend"))

PACKAGES = {
    "pymupdf": "pymupdf",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "multipart": "python-multipart",
    "openai": "openai",
    "dotenv": "python-dotenv",
    "pypdf": "pypdf",
    "pdfplumber": "pdfplumber",
    "yaml": "PyYAML",
    "pytesseract": "pytesseract",
    "PIL": "pillow",
}
# Hosts that process inference in the EU/EEA for the model we use.
EU_HOSTS = {"api.scaleway.ai": "Scaleway, Paris (FR)", "api.eu.mistral.ai": "Mistral EU endpoint (EU/EFTA)"}


class Report:
    def __init__(self) -> None:
        self.required_failed = False

    def line(self, status: str, name: str, detail: str = "", hint: str = "", required: bool = False) -> None:
        print(f"  {status:<4}  {name:<28} {detail}".rstrip())
        for row in hint.splitlines():
            print(f"        {row}")
        if status == "FAIL" and required:
            self.required_failed = True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check PrzetarGO prerequisites.")
    parser.add_argument("--check-llm", action="store_true", help="Send one tiny request to the configured Mistral endpoint.")
    parser.add_argument("--startup", action="store_true", help="Short check used by start.sh / start.bat before the server starts.")
    args = parser.parse_args(argv)

    report = Report()
    print("PrzetarGO doctor")
    _python(report)
    packages_ok = _packages(report)
    _tesseract(report, packages_ok)
    _folders(report)
    if args.startup:
        _port(report)
    _llm(report, packages_ok, args.check_llm)
    if report.required_failed:
        print("Some required checks failed. Fix them before starting PrzetarGO.")
        return 1
    return 0


def _python(report: Report) -> None:
    version = ".".join(map(str, sys.version_info[:3]))
    if sys.version_info >= (3, 13):
        report.line("PASS", "Python", version)
    else:
        report.line("FAIL", "Python", f"{version} (3.13+ required)", _python_hint(), required=True)


def _python_hint() -> str:
    system = platform.system()
    if system == "Darwin":
        return "Install: brew install python@3.13   (or the installer from python.org)"
    if system == "Windows":
        return "Install Python 3.13 from python.org (tick 'Add python.exe to PATH'), or: winget install -e --id Python.Python.3.13"
    return "Install: sudo apt install python3.13 python3.13-venv   (Ubuntu: add ppa:deadsnakes/ppa first if needed)"


def _packages(report: Report) -> bool:
    missing = []
    for module, package in PACKAGES.items():
        try:
            importlib.import_module(module)
        except Exception:
            missing.append(package)
    if missing:
        report.line(
            "FAIL",
            "Python packages",
            "missing: " + ", ".join(missing),
            f"Install: {Path(sys.executable).name} -m pip install -r requirements.txt",
            required=True,
        )
        return False
    report.line("PASS", "Python packages", "all installed")
    return True


def _tesseract(report: Report, packages_ok: bool) -> None:
    command = ""
    if packages_ok:
        from pdf_reader import _configure_tesseract, find_tesseract

        command = find_tesseract()
        if command:
            _configure_tesseract()
    else:
        command = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract") or ""
    if not command:
        report.line("FAIL", "Tesseract executable", "not found (scanned PDFs cannot be read)", _tesseract_hint())
        for name in ("Tesseract version", "Polish OCR data (pol)", "English OCR data (eng)", "OCR test"):
            report.line("SKIP", name)
        return
    report.line("PASS", "Tesseract executable", command)

    version = _run([command, "--version"])
    first = (version or "").splitlines()[0] if version else ""
    number = first.replace("tesseract", "").strip().lstrip("v")
    if not first:
        report.line("FAIL", "Tesseract version", "could not run tesseract --version", _tesseract_hint())
    elif number[:1].isdigit() and int(number.split(".")[0]) < 4:
        report.line("FAIL", "Tesseract version", f"{number} (4.x or 5.x needed)", _tesseract_hint())
    else:
        report.line("PASS", "Tesseract version", number)

    listed = _run([command, "--list-langs"]) or ""
    languages = {line.strip() for line in listed.splitlines()[1:] if line.strip()}
    if "pol" in languages:
        report.line("PASS", "Polish OCR data (pol)", "installed")
    else:
        report.line("FAIL", "Polish OCR data (pol)", "missing (scanned Polish PDFs will read badly or not at all)", _language_hint("pol"))
    if "eng" in languages:
        report.line("PASS", "English OCR data (eng)", "installed")
    else:
        report.line("FAIL", "English OCR data (eng)", "missing", _language_hint("eng"))

    if not packages_ok or "pol" not in languages:
        report.line("SKIP", "OCR test", "needs the Python packages and Polish data")
        return
    seen = _ocr_smoke_test()
    if "2026" in seen and "ODWO" in seen.upper():
        report.line("PASS", "OCR test", "read a rendered test page")
    else:
        report.line("FAIL", "OCR test", f"unexpected text: {seen.strip()[:40]!r}", "Reinstall Tesseract, then run: python doctor.py")


def _ocr_smoke_test() -> str:
    try:
        import io

        import pymupdf
        import pytesseract
        from PIL import Image

        pdf = pymupdf.open()
        page = pdf.new_page(width=420, height=120)
        page.insert_text((24, 72), "ODWOLANIE 2026", fontsize=30)
        pixmap = page.get_pixmap(dpi=200, colorspace=pymupdf.csGRAY, alpha=False)
        pdf.close()
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        return pytesseract.image_to_string(image, lang="pol", config="--psm 6", timeout=30)
    except Exception as exc:
        return f"error: {type(exc).__name__}"


def _tesseract_hint() -> str:
    system = platform.system()
    if system == "Darwin":
        return "Install: brew install tesseract tesseract-lang"
    if system == "Windows":
        return (
            "Install Tesseract 5.x from https://github.com/UB-Mannheim/tesseract/wiki\n"
            "(in the installer, tick Polish under 'Additional language data').\n"
            "Default path: C:\\Program Files\\Tesseract-OCR\\tesseract.exe. If it is elsewhere, set\n"
            "TESSERACT_CMD=C:\\path\\to\\tesseract.exe in backend\\.env or add its folder to PATH."
        )
    return "Install: sudo apt install tesseract-ocr tesseract-ocr-pol tesseract-ocr-eng"


def _language_hint(language: str) -> str:
    system = platform.system()
    if system == "Darwin":
        return "Install: brew install tesseract-lang"
    if system == "Windows":
        return (
            f"Download {language}.traineddata from https://github.com/tesseract-ocr/tessdata_fast\n"
            "into the tessdata folder next to tesseract.exe (e.g. C:\\Program Files\\Tesseract-OCR\\tessdata)."
        )
    return f"Install: sudo apt install tesseract-ocr-{language}"


def _folders(report: Report) -> None:
    problems = []
    for name in ("input", "output"):
        folder = ROOT / name
        try:
            folder.mkdir(exist_ok=True)
            probe = folder / ".doctor-write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            problems.append(f"{name}/ ({exc.strerror})")
    if problems:
        report.line("FAIL", "input/ and output/ folders", "not writable: " + ", ".join(problems), required=True)
    else:
        report.line("PASS", "input/ and output/ folders", "writable")


def _port(report: Report) -> None:
    port = int(os.environ.get("PORT", "8000"))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            hint = f"Stop the other program, or pick another port: PORT={port + 1} ./start.sh   (Windows: set PORT={port + 1} && start.bat)"
            report.line("FAIL", "Port", f"127.0.0.1:{port} is already in use", hint, required=True)
            return
    report.line("PASS", "Port", f"127.0.0.1:{port} is free")


def _llm(report: Report, packages_ok: bool, live: bool) -> None:
    if not packages_ok:
        report.line("SKIP", "Mistral (optional)", "needs the Python packages")
        return
    from odwolania.llm import LLMClient, llm_setting

    base_url = llm_setting("LLM_BASE_URL")
    model = llm_setting("LLM_MODEL")
    host = urlparse(base_url).hostname or base_url
    region = EU_HOSTS.get(host)
    if region:
        report.line("PASS", "Mistral endpoint", f"{host} - {region}")
    else:
        report.line("FAIL", "Mistral endpoint", f"{host} - EU/EEA processing not verified for this host")
    report.line("PASS", "Mistral model", model)
    if not llm_setting("LLM_API_KEY"):
        report.line("SKIP", "Mistral API key", "not set; deterministic mode only (set MISTRAL_API_KEY for hybrid)")
        return
    report.line("PASS", "Mistral API key", "set (value hidden)")
    if not live:
        report.line("SKIP", "Mistral connection", "run python doctor.py --check-llm to test")
        return
    try:
        LLMClient().ping()
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        detail = f"rejected (HTTP {status})" if status else f"endpoint unreachable ({type(exc).__name__})"
        hint = "Check the key and model name." if status else "Check the network, or try MISTRAL_BASE_URL=https://api.scaleway.ai/v1."
        report.line("FAIL", "Mistral connection", detail, hint)
        return
    report.line("PASS", "Mistral connection", "the API accepted the key and model")


def _run(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return (completed.stdout or "") + (completed.stderr or "")


if __name__ == "__main__":
    raise SystemExit(main())

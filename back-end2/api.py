"""HTTP interface and local web page for PrzetarGO.

Extraction itself lives in engine.py, which the batch CLI (../main.py) also uses.
"""

import json
import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from engine import LLM_MODES, MODES, RULES, envelope, extract_document
from pipeline import process_pdf
from pdf_reader import forget_pdf, ocr_available
from odwolania.llm import (
    LLMAuthError,
    LLMClient,
    hosted,
    llm_configured,
    server_key_configured,
    set_llm_credentials,
)

MAX_BYTES = 20 * 1024 * 1024
# The evaluation set is 150 documents; the page uploads them in batches of 10 into one case.
MAX_FILES = 150
REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "front-end"
DATASET = REPO_ROOT / "UZP-hacknation-task" / "dane"
INPUT_ROOT = REPO_ROOT / "input"
OUTPUT_ROOT = REPO_ROOT / "output"
CASE_NAME = re.compile(r"^przyklad_\d{2}$")
CASE_DIR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
# PDFs placed straight in input/ rather than in a case folder; their JSON goes straight to output/.
ROOT_CASE = "."
SCAN_GROUPS = ("odwolania", "pelnomocnictwa", "potwierdzenia")

def _show_llm_calls() -> None:
    log = logging.getLogger("odwolania.llm")
    log.setLevel(logging.INFO)
    log.propagate = False
    if log.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)


_show_llm_calls()

app = FastAPI(title="PrzetarGO")
class PrivateNetworkMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
app.add_middleware(PrivateNetworkMiddleware)


_STATS_LIVE = REPO_ROOT / "reports" / "stats.json"
_STATS_FALLBACK = FRONTEND / "assets" / "stats" / "stats.json"
_CHARTS_LIVE = REPO_ROOT / "reports" / "charts"
_CHARTS_FALLBACK = FRONTEND / "assets" / "stats"
_CHART_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}\.png$")


def _prefer(live: Path, fallback: Path) -> Path | None:
    if live.is_file():
        return live
    if fallback.is_file():
        return fallback
    return None


@app.get("/api/stats")
def stats():
    path = _prefer(_STATS_LIVE, _STATS_FALLBACK)
    if path is None:
        raise HTTPException(
            status_code=404,
            detail="Brak reports/stats.json. Uruchom ewaluację, aby go utworzyć.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/charts/{name}")
def chart(name: str):
    if not _CHART_NAME.fullmatch(name):
        raise HTTPException(status_code=404, detail="Nieznany wykres.")
    path = _prefer(_CHARTS_LIVE / name, _CHARTS_FALLBACK / name)
    if path is None:
        raise HTTPException(status_code=404, detail="Nieznany wykres.")
    return FileResponse(path, media_type="image/png")


@app.exception_handler(LLMAuthError)
def llm_auth_failed(request: Request, exc: LLMAuthError):
    return JSONResponse(status_code=401, content={"detail": "llm_key_rejected", "reason": str(exc)})


@app.get("/api/health")
def health():
    engine = "deterministic+mistral" if llm_configured() else "deterministic"
    return {
        "status": "ok",
        "engine": engine,
        "hosted": hosted(),
        "server_key": server_key_configured(),
        "ocr": ocr_available(),
    }


@app.post("/api/llm/check")
def check_llm(request: Request):
    """Try the key the browser sent with one tiny completion."""
    _use_request_llm(request)
    if not llm_configured():
        return {"ok": False, "error": "No Mistral API key."}
    try:
        client = LLMClient()
        client.ping()
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        if status:
            return {"ok": False, "error": f"The API rejected the request (HTTP {status}). Check the key and model."}
        return {"ok": False, "error": f"Could not reach the API endpoint ({type(exc).__name__})."}
    return {"ok": True, "model": client.model}


@app.get("/api/samples")
def list_samples():
    """Example cases from the task data, so visitors can try the app without their own PDFs."""
    samples = []
    if not DATASET.is_dir():
        return {"samples": samples}
    for folder in sorted(path for path in DATASET.iterdir() if CASE_NAME.fullmatch(path.name)):
        files = [_sample_entry(pdf, pdf.name) for pdf in sorted(folder.glob("*.pdf"))]
        if files:
            samples.append({"id": folder.name, "kind": "text", "files": files})
    scans = DATASET / "skany"
    numbers = sorted({path.name for group in SCAN_GROUPS for path in (scans / group).glob("[0-9]*") if path.is_dir()})
    for number in numbers:
        # Every scan is named <number>.pdf, so the group goes into the visible name.
        files = [
            _sample_entry(pdf, f"{group}_{pdf.name}")
            for group in SCAN_GROUPS
            for pdf in sorted((scans / group / number).glob("*.pdf"))
        ]
        if files:
            samples.append({"id": f"skany_{number}", "kind": "scan", "files": files})
    return {"samples": samples}


@app.get("/api/samples/file")
def sample_file(path: str):
    target = (DATASET / path).resolve()
    if not target.is_relative_to(DATASET.resolve()) or target.suffix.lower() != ".pdf" or not target.is_file():
        raise HTTPException(status_code=404, detail="Unknown file.")
    return FileResponse(target, media_type="application/pdf", filename=target.name)


def _sample_entry(path: Path, name: str) -> dict:
    return {"path": path.relative_to(DATASET).as_posix(), "name": name}


def _use_request_llm(request: Request) -> None:
    """Read the Mistral settings sent with this request. They are never logged or stored."""
    base_url = request.headers.get("x-llm-base-url", "")
    if base_url and hosted():
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise HTTPException(status_code=400, detail="The API base URL must start with https://")
    set_llm_credentials(
        request.headers.get("x-llm-key", ""),
        base_url,
        request.headers.get("x-llm-model", ""),
    )


def _require_llm(mode: str) -> None:
    if mode in LLM_MODES and not llm_configured():
        raise HTTPException(status_code=400, detail="llm_key_missing")


def _require_local() -> None:
    if hosted():
        raise HTTPException(status_code=404, detail="Not available on the hosted site.")


@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    return await _process_upload(file)


class ExampleRequest(BaseModel):
    case: str = "przyklad_01"


@app.post("/api/extract/example")
def extract_example(body: ExampleRequest):
    if not CASE_NAME.fullmatch(body.case):
        return {"results": [], "error": "Unknown case."}
    folder = (DATASET / body.case).resolve()
    if not folder.is_relative_to(DATASET.resolve()) or not folder.is_dir():
        return {"results": [], "error": "Unknown case."}
    results = []
    for pdf in sorted(folder.glob("*.pdf")):
        try:
            payload, diagnostic = process_pdf(pdf, RULES)
            diagnostic["file"] = pdf.name
            item = envelope(pdf.name, payload, diagnostic, None)
        except Exception:
            item = envelope(pdf.name, {}, None, "The PDF could not be read.")
        item["size"] = pdf.stat().st_size
        results.append(item)
    return {"results": results, "case": body.case}


# A plain def runs in the thread pool, so one long Mistral batch does not block the others.
@app.post("/api/extract/batch")
def extract_batch(
    request: Request,
    files: list[UploadFile] = File(...),
    mode: str = Form("regular"),
    case: str = Form(""),
    nocache: str = Form("0"),
    nocache_query: str = Query("", alias="nocache"),
):
    if mode not in MODES:
        raise HTTPException(status_code=400, detail="mode must be regular, mistral, or mistral_only")
    from odwolania.llm import current_usage, set_skip_cache, start_usage

    _use_request_llm(request)
    _require_llm(mode)
    start_usage()
    set_skip_cache(_enabled(nocache) or _enabled(nocache_query))
    started = time.perf_counter()
    selected = files[:MAX_FILES]
    if hosted():
        case = None
    elif not re.fullmatch(r"case\d{1,6}", case):
        case = _next_case_name()
    results = []
    for upload in selected:
        filename = Path(upload.filename or "document.pdf").name
        data = upload.file.read()
        if case is None:
            item = _process_bytes(filename, data, mode)
            item["size"] = len(data)
        else:
            item = _save_and_process(filename, data, mode, INPUT_ROOT / case, case)
        results.append(item)
    elapsed = time.perf_counter() - started
    count = len(results)
    return {
        "results": results,
        "truncated": len(files) > MAX_FILES,
        "mode": mode,
        "usage": current_usage(),
        "elapsed_seconds": round(elapsed, 3),
        "seconds_per_file": round(elapsed / count, 3) if count else 0.0,
        "case": case,
    }


class InputRequest(BaseModel):
    cases: list[str] = []
    mode: str = "regular"


@app.get("/api/input")
def list_input():
    if hosted():
        return {"cases": []}
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    cases = []
    loose = _pdfs(INPUT_ROOT)
    if loose:
        cases.append({"name": ROOT_CASE, "files": [{"name": pdf.name, "size": pdf.stat().st_size} for pdf in loose]})
    for folder in sorted(path for path in INPUT_ROOT.iterdir() if path.is_dir() and CASE_DIR.fullmatch(path.name)):
        files = [{"name": pdf.name, "size": pdf.stat().st_size} for pdf in _pdfs(folder)]
        cases.append({"name": folder.name, "files": files})
    return {"cases": cases, "input_root": str(INPUT_ROOT), "output_root": str(OUTPUT_ROOT)}


def _pdfs(folder: Path) -> list[Path]:
    return sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")


class InputFileRequest(BaseModel):
    case: str
    file: str
    mode: str = "regular"


@app.post("/api/extract/input/file")
def extract_input_file(body: InputFileRequest, request: Request):
    """One PDF from input/ per request, so the page can show progress for any number of files."""
    _require_local()
    if body.mode not in MODES:
        raise HTTPException(status_code=400, detail="mode must be regular, mistral, or mistral_only")
    folder = _case_dir(body.case)
    if folder is None or Path(body.file).name != body.file:
        raise HTTPException(status_code=404, detail="Unknown file.")
    pdf = folder / body.file
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="Unknown file.")
    from odwolania.llm import current_usage, set_skip_cache, start_usage

    _use_request_llm(request)
    _require_llm(body.mode)
    start_usage()
    set_skip_cache(False)
    started = time.perf_counter()
    item = extract_document(pdf, pdf.name, body.mode)
    item["size"] = pdf.stat().st_size
    item["case"] = body.case
    item["output"] = _write_output(body.case, pdf.name, item["result"])
    return {
        "result": item,
        "mode": body.mode,
        "usage": current_usage(),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }


@app.delete("/api/input")
def delete_input():
    """Remove case files from input/. The output folder is not touched."""
    _require_local()
    removed = []
    if INPUT_ROOT.is_dir():
        root = INPUT_ROOT.resolve()
        for path in list(INPUT_ROOT.iterdir()):
            if path.name == ".gitkeep":
                continue
            target = path.resolve()
            if not target.is_relative_to(root):
                continue
            if path.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            removed.append(path.name)
    return {"removed": removed}


@app.post("/api/extract/input")
def extract_input(body: InputRequest, request: Request):
    _require_local()
    if body.mode not in MODES:
        raise HTTPException(status_code=400, detail="mode must be regular, mistral, or mistral_only")
    from odwolania.llm import current_usage, set_skip_cache, start_usage

    _use_request_llm(request)
    _require_llm(body.mode)
    start_usage()
    set_skip_cache(False)
    started = time.perf_counter()
    results = []
    seen = 0
    for name in body.cases:
        folder = _case_dir(name)
        if folder is None:
            continue
        for pdf in sorted(folder.glob("*.pdf")):
            if seen >= MAX_FILES:
                break
            seen += 1
            item = extract_document(pdf, pdf.name, body.mode)
            item["size"] = pdf.stat().st_size
            item["output"] = _write_output(name, pdf.name, item["result"])
            results.append(item)
        if seen >= MAX_FILES:
            break
    elapsed = time.perf_counter() - started
    count = len(results)
    return {
        "results": results,
        "truncated": seen >= MAX_FILES,
        "mode": body.mode,
        "usage": current_usage(),
        "elapsed_seconds": round(elapsed, 3),
        "seconds_per_file": round(elapsed / count, 3) if count else 0.0,
    }


def _enabled(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


async def _process_upload(upload: UploadFile, mode: str = "regular"):
    filename = Path(upload.filename or "document.pdf").name
    data = await upload.read()
    return _process_bytes(filename, data, mode)


def _save_and_process(filename: str, data: bytes, mode: str, case_dir: Path, case: str):
    rejected = pdf_rejection(filename, data)
    if rejected or not data or len(data) > MAX_BYTES:
        return _process_bytes(filename, data, mode)
    case_dir.mkdir(parents=True, exist_ok=True)
    destination = case_dir / filename
    copy = 2
    while destination.exists():
        destination = case_dir / f"{Path(filename).stem}_{copy}{Path(filename).suffix}"
        copy += 1
    filename = destination.name
    destination.write_bytes(data)
    item = extract_document(destination, filename, mode)
    item["size"] = len(data)
    item["output"] = _write_output(case, filename, item["result"])
    return item


def _process_bytes(filename: str, data: bytes, mode: str):
    from odwolania.llm import set_llm_document

    set_llm_document(filename)
    rejected = pdf_rejection(filename, data)
    if rejected:
        return envelope(filename, {}, None, rejected, status="rejected")
    if not data:
        return envelope(filename, {}, None, "The file is empty.")
    if len(data) > MAX_BYTES:
        return envelope(filename, {}, None, "The file is larger than 20 MB.")
    handle, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(handle, "wb") as stored:
            stored.write(data)
        return extract_document(Path(path), filename, mode)
    finally:
        forget_pdf(path)
        try:
            os.unlink(path)
        except OSError:
            pass


def _case_dir(name: str) -> Path | None:
    if name == ROOT_CASE:
        return INPUT_ROOT if INPUT_ROOT.is_dir() else None
    if not CASE_DIR.fullmatch(name or ""):
        return None
    folder = (INPUT_ROOT / name).resolve()
    if not folder.is_relative_to(INPUT_ROOT.resolve()) or not folder.is_dir():
        return None
    return folder


def _next_case_name() -> str:
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    numbers = []
    for path in INPUT_ROOT.iterdir():
        match = re.fullmatch(r"case(\d+)", path.name)
        if match and path.is_dir():
            numbers.append(int(match.group(1)))
    return f"case{max(numbers, default=0) + 1}"


def _write_output(case: str, filename: str, payload: dict) -> str:
    folder = OUTPUT_ROOT if case == ROOT_CASE else OUTPUT_ROOT / case
    destination = folder / f"{Path(filename).stem}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination.relative_to(REPO_ROOT).as_posix()


def pdf_rejection(filename: str, data: bytes) -> str | None:
    """A file is a PDF only when the name and the header both say so."""
    name = Path(filename or "").name
    if name.lower().endswith(".pdf") and data.startswith(b"%PDF"):
        return None
    return f"Rejected: {name} – not a PDF"


@app.get("/api/sample/{case}/{filename}")
def sample_pdf(case: str, filename: str):
    if not CASE_NAME.fullmatch(case) or Path(filename).name != filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=404, detail="Unknown file.")
    path = (DATASET / case / filename).resolve()
    if not path.is_relative_to(DATASET.resolve()) or not path.is_file():
        raise HTTPException(status_code=404, detail="Unknown file.")
    return FileResponse(path, media_type="application/pdf", filename=filename)


app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")))

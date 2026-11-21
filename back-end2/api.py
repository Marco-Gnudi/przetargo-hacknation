"""HTTP interface for the existing deterministic extractor.

The CLI in main.py stays the evaluation entry point. This module only
receives uploads, calls process_pdf, and deletes the temporary file.
"""

import json
import logging
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from pipeline import load_rules, process_pdf
from llm_fill import extract_bielik_only, fill_with_bielik, review_marks, tag_rules

MAX_BYTES = 20 * 1024 * 1024
MAX_FILES = 30
REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "front-end"
DATASET = REPO_ROOT / "UZP-hacknation-task" / "dane"
INPUT_ROOT = REPO_ROOT / "input"
OUTPUT_ROOT = REPO_ROOT / "output"
CASE_NAME = re.compile(r"^przyklad_\d{2}$")
CASE_DIR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
RULES = load_rules()

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


@app.get("/api/health")
def health():
    engine = "deterministic+bielik" if _bielik_configured() else "deterministic"
    return {"status": "ok", "engine": engine}


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
            item = _envelope(pdf.name, payload, diagnostic, None)
        except Exception:
            item = _envelope(pdf.name, {}, None, "The PDF could not be read.")
        item["size"] = pdf.stat().st_size
        results.append(item)
    return {"results": results, "case": body.case}


@app.post("/api/extract/batch")
async def extract_batch(
    files: list[UploadFile] = File(...),
    mode: str = Form("regular"),
    nocache: str = Form("0"),
    nocache_query: str = Query("", alias="nocache"),
):
    if mode not in ("regular", "bielik", "bielik_only"):
        raise HTTPException(status_code=400, detail="mode must be regular, bielik, or bielik_only")
    from odwolania.llm import current_usage, set_skip_cache, start_usage

    start_usage()
    set_skip_cache(_enabled(nocache) or _enabled(nocache_query))
    started = time.perf_counter()
    selected = files[:MAX_FILES]
    case = _next_case_name()
    case_dir = INPUT_ROOT / case
    results = []
    for upload in selected:
        results.append(await _save_and_process(upload, mode, case_dir, case))
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
    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    cases = []
    for folder in sorted(path for path in INPUT_ROOT.iterdir() if path.is_dir() and CASE_DIR.fullmatch(path.name)):
        files = []
        for pdf in sorted(folder.glob("*.pdf")):
            files.append({"name": pdf.name, "size": pdf.stat().st_size})
        cases.append({"name": folder.name, "files": files})
    return {"cases": cases}


@app.delete("/api/input")
def delete_input():
    """Remove case files from input/. The output folder is not touched."""
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
def extract_input(body: InputRequest):
    if body.mode not in ("regular", "bielik", "bielik_only"):
        raise HTTPException(status_code=400, detail="mode must be regular, bielik, or bielik_only")
    from odwolania.llm import current_usage, set_skip_cache, start_usage

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
            item = _extract_path(pdf, pdf.name, body.mode)
            item["size"] = pdf.stat().st_size
            item["output"] = _write_output(folder.name, pdf.name, item["result"])
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


def _bielik_configured() -> bool:
    import os

    from odwolania.llm import load_env

    load_env()
    return all(os.environ.get(name) for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"))


def _enabled(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


async def _process_upload(upload: UploadFile, mode: str = "regular"):
    filename = Path(upload.filename or "document.pdf").name
    data = await upload.read()
    return _process_bytes(filename, data, mode)


async def _save_and_process(upload: UploadFile, mode: str, case_dir: Path, case: str):
    filename = Path(upload.filename or "document.pdf").name
    data = await upload.read()
    rejected = pdf_rejection(filename, data)
    if rejected or not data or len(data) > MAX_BYTES:
        return _process_bytes(filename, data, mode)
    case_dir.mkdir(parents=True, exist_ok=True)
    destination = case_dir / filename
    destination.write_bytes(data)
    item = _extract_path(destination, filename, mode)
    item["size"] = len(data)
    item["output"] = _write_output(case, filename, item["result"])
    return item


def _process_bytes(filename: str, data: bytes, mode: str):
    from odwolania.llm import set_llm_document

    set_llm_document(filename)
    rejected = pdf_rejection(filename, data)
    if rejected:
        return _envelope(filename, {}, None, rejected, status="rejected")
    if not data:
        return _envelope(filename, {}, None, "The file is empty.")
    if len(data) > MAX_BYTES:
        return _envelope(filename, {}, None, "The file is larger than 20 MB.")
    handle, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(handle, "wb") as stored:
            stored.write(data)
        return _extract_path(Path(path), filename, mode)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _extract_path(path: Path, filename: str, mode: str):
    from odwolania.llm import set_llm_document

    set_llm_document(filename)
    try:
        if mode == "bielik_only":
            payload, document_type, sources, raw = extract_bielik_only(path)
            diagnostic = {"document_type": document_type, "warnings": [], "file": filename}
            item = _envelope(filename, payload, diagnostic, None)
            item["sources"] = sources
            item["raw"] = raw
            return item
        payload, diagnostic = process_pdf(path, RULES)
        diagnostic["file"] = filename
        sources = tag_rules(payload)
        raw = payload
        bielik: dict = {}
        if mode == "bielik":
            try:
                payload, document_type, sources, bielik, raw = fill_with_bielik(
                    path, payload, diagnostic["document_type"]
                )
                diagnostic = dict(diagnostic)
                diagnostic["document_type"] = document_type
            except Exception:
                diagnostic = dict(diagnostic)
                diagnostic["warnings"] = list(diagnostic.get("warnings") or []) + [
                    "Bielik fill failed; deterministic values were kept."
                ]
                raw = payload
                bielik = {}
        item = _envelope(filename, payload, diagnostic, None)
        item["sources"] = sources
        item["raw"] = raw
        if mode == "bielik":
            item["review"] = review_marks(payload, sources, bielik)
        return item
    except Exception:
        return _envelope(filename, {}, None, "The PDF could not be read.")


def _case_dir(name: str) -> Path | None:
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
    destination = OUTPUT_ROOT / case / f"{Path(filename).stem}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination.relative_to(REPO_ROOT).as_posix()


def pdf_rejection(filename: str, data: bytes) -> str | None:
    """A file is a PDF only when the name and the header both say so."""
    name = Path(filename or "").name
    if name.lower().endswith(".pdf") and data.startswith(b"%PDF"):
        return None
    return f"Rejected: {name} – not a PDF"


def _envelope(filename, payload, diagnostic, error, status=None):
    document_type = diagnostic["document_type"] if diagnostic else "unknown"
    if status is None:
        if error:
            status = "error"
        elif document_type == "unknown":
            status = "unrecognized"
        else:
            status = "ok"
    return {
        "filename": filename,
        "document_type": document_type,
        "status": status,
        "result": payload if isinstance(payload, dict) else {},
        "warnings": list(diagnostic["warnings"]) if diagnostic else [],
        "error": error,
    }


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

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))

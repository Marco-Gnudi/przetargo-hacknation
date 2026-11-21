"""HTTP interface for the existing deterministic extractor.

The CLI in main.py stays the evaluation entry point. This module only
receives uploads, calls process_pdf, and deletes the temporary file.
"""

import os
import re
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from pipeline import load_rules, process_pdf

MAX_BYTES = 20 * 1024 * 1024
MAX_FILES = 30
FRONTEND = Path(__file__).resolve().parents[1] / "front-end"
DATASET = Path(__file__).resolve().parents[1] / "UZP-hacknation-task" / "dane"
CASE_NAME = re.compile(r"^przyklad_\d{2}$")
RULES = load_rules()

app = FastAPI(title="PrzetarGO")
class PrivateNetworkMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.add_middleware(PrivateNetworkMiddleware)


@app.get("/api/health")
def health():
    return {"status": "ok", "engine": "deterministic"}


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
async def extract_batch(files: list[UploadFile] = File(...)):
    selected = files[:MAX_FILES]
    results = []
    for upload in selected:
        results.append(await _process_upload(upload))
    return {"results": results, "truncated": len(files) > MAX_FILES}


async def _process_upload(upload: UploadFile):
    filename = Path(upload.filename or "document.pdf").name
    data = await upload.read()
    if not filename.lower().endswith(".pdf"):
        return _envelope(filename, {}, None, "Only PDF files are accepted.")
    if not data:
        return _envelope(filename, {}, None, "The file is empty.")
    if len(data) > MAX_BYTES:
        return _envelope(filename, {}, None, "The file is larger than 20 MB.")
    if not data.startswith(b"%PDF"):
        return _envelope(filename, {}, None, "The file is not a PDF.")

    handle, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(handle, "wb") as stored:
            stored.write(data)
        payload, diagnostic = process_pdf(path, RULES)
        diagnostic["file"] = filename
        return _envelope(filename, payload, diagnostic, None)
    except Exception:
        return _envelope(filename, {}, None, "The PDF could not be read.")
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _envelope(filename, payload, diagnostic, error):
    document_type = diagnostic["document_type"] if diagnostic else "unknown"
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


app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))

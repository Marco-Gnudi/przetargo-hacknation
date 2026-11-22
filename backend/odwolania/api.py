"""HTTP API for the PrzetarGO front-end. The CLI stays in main.py."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from odwolania.pipeline import process_file

app = FastAPI(title="Odwołania2JSON")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/process")
async def process_documents(
    mode: str = Form(...),
    files: list[UploadFile] = File(...),
) -> dict:
    if mode not in ("regular", "mistral"):
        raise HTTPException(status_code=400, detail="mode must be regular or mistral")
    if not files:
        raise HTTPException(status_code=400, detail="at least one PDF is required")

    results = []
    for upload in files:
        content = await upload.read()
        filename = Path(upload.filename or "document.pdf").name
        results.append(_process_upload(filename, content, mode))
    return {"files": results}


def _process_upload(filename: str, content: bytes, mode: str) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
        handle.write(content)
        path = Path(handle.name)
    try:
        processed = process_file(path, mode=mode, filename=filename)
    finally:
        path.unlink(missing_ok=True)
    return {
        "filename": processed.filename,
        "type": processed.document_type,
        "json": processed.data,
        "sources": processed.sources,
    }

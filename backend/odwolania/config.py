"""Load document-type config. Paths are anchored at the repo root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
CONFIG_PATH = BACKEND_ROOT / "config" / "document_types.yaml"

# The brief calls this folder data/. In this repo it was moved.
_DATA_DIR_NAMES = ("data", "UZP-hacknation-task")


@dataclass(frozen=True)
class DocumentType:
    id: str
    output_filename: str
    keywords: tuple[str, ...]
    fields: tuple[str, ...]


def task_data_dir() -> Path:
    """Directory that holds dane/, oczekiwane-json/ and szablon-aplikacja/."""
    for name in _DATA_DIR_NAMES:
        candidate = REPO_ROOT / name
        if (candidate / "dane").is_dir() and (candidate / "oczekiwane-json").is_dir():
            return candidate
    looked = ", ".join(str(REPO_ROOT / name) for name in _DATA_DIR_NAMES)
    raise FileNotFoundError(f"Task data directory not found. Looked at: {looked}")


def load_document_types(path: Path | None = None) -> list[DocumentType]:
    config_path = path or CONFIG_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    entries = raw.get("document_types") if isinstance(raw, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"document_types must be a non-empty list in {config_path}")

    types: list[DocumentType] = []
    for entry in entries:
        types.append(_parse_entry(entry, config_path))
    return types


def _parse_entry(entry: object, config_path: Path) -> DocumentType:
    if not isinstance(entry, dict):
        raise ValueError(f"Each document type must be a mapping in {config_path}")
    missing = [key for key in ("id", "output_filename", "keywords", "fields") if key not in entry]
    if missing:
        raise ValueError(f"Document type missing {missing} in {config_path}")
    keywords = entry["keywords"]
    fields = entry["fields"]
    if not isinstance(keywords, list) or not keywords:
        raise ValueError(f"keywords must be a non-empty list for {entry.get('id')}")
    if not isinstance(fields, list) or not fields:
        raise ValueError(f"fields must be a non-empty list for {entry.get('id')}")
    return DocumentType(
        id=str(entry["id"]),
        output_filename=str(entry["output_filename"]),
        keywords=tuple(str(item) for item in keywords),
        fields=tuple(str(item) for item in fields),
    )

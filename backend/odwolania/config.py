"""Load document-type config. Paths are anchored at the repo root."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
CONFIG_PATH = BACKEND_ROOT / "config" / "document_types.yaml"

# The brief calls this folder data/. In this repo it was moved.
_DATA_DIR_NAMES = ("data", "UZP-hacknation-task")


@dataclass(frozen=True)
class Keyword:
    pattern: str
    weight: float


@dataclass(frozen=True)
class DocumentType:
    id: str
    output_filename: str
    keywords: tuple[Keyword, ...]
    fields: tuple[str, ...]


@dataclass(frozen=True)
class Settings:
    threshold: float
    margin: float
    document_types: tuple[DocumentType, ...]


def task_data_dir() -> Path:
    """Directory that holds dane/, oczekiwane-json/ and szablon-aplikacja/."""
    for name in _DATA_DIR_NAMES:
        candidate = REPO_ROOT / name
        if (candidate / "dane").is_dir() and (candidate / "oczekiwane-json").is_dir():
            return candidate
    looked = ", ".join(str(REPO_ROOT / name) for name in _DATA_DIR_NAMES)
    raise FileNotFoundError(f"Task data directory not found. Looked at: {looked}")


def load_document_types(path: Path | None = None) -> list[DocumentType]:
    return list(load_settings(path).document_types)


@lru_cache(maxsize=4)
def load_settings(path: Path | None = None) -> Settings:
    config_path = path or CONFIG_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Config must be a mapping: {config_path}")
    entries = raw.get("document_types")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"document_types must be a non-empty list in {config_path}")
    try:
        threshold = float(raw.get("threshold", 1))
        margin = float(raw.get("margin", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"threshold and margin must be numbers in {config_path}") from exc

    types = tuple(_parse_entry(entry, config_path) for entry in entries)
    return Settings(threshold=threshold, margin=margin, document_types=types)


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
    parsed = tuple(_parse_keyword(item, entry.get("id"), config_path) for item in keywords)
    return DocumentType(
        id=str(entry["id"]),
        output_filename=str(entry["output_filename"]),
        keywords=parsed,
        fields=tuple(str(item) for item in fields),
    )


def _parse_keyword(item: object, type_id: object, config_path: Path) -> Keyword:
    if isinstance(item, str):
        pattern, weight = re.escape(item), 1.0
    elif isinstance(item, dict):
        raw_pattern = item.get("pattern", item.get("match"))
        if not isinstance(raw_pattern, str) or not raw_pattern:
            raise ValueError(f"Keyword in {type_id} needs a pattern ({config_path})")
        try:
            weight = float(item.get("weight", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Bad weight for {type_id} in {config_path}") from exc
        pattern = raw_pattern if item.get("regex", True) else re.escape(raw_pattern)
    else:
        raise ValueError(f"Keyword in {type_id} must be a string or mapping ({config_path})")
    try:
        re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"Invalid pattern for {type_id}: {pattern}") from exc
    return Keyword(pattern=pattern, weight=weight)

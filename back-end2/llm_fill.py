"""Fill nulls from the Bielik pipeline in backend/. Does not replace rule values."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(1, str(_BACKEND))


def merge_payload(
    base: dict,
    incoming: dict,
    incoming_sources: dict[str, str] | None = None,
) -> tuple[dict, dict[str, str]]:
    """Keep deterministic values. Copy Bielik only into null or missing fields."""
    result = copy.deepcopy(base) if isinstance(base, dict) else {}
    sources: dict[str, str] = {}
    _tag(result, sources, "rule", "")
    _fill(result, incoming if isinstance(incoming, dict) else {}, sources, "", incoming_sources or {})
    return result, sources


def tag_rules(payload: dict) -> dict[str, str]:
    sources: dict[str, str] = {}
    _tag(payload if isinstance(payload, dict) else {}, sources, "rule", "")
    return sources


def fill_with_bielik(pdf_path: Path, payload: dict, document_type: str) -> tuple[dict, str, dict[str, str]]:
    """Run backend.odwolania in bielik mode and fill only what rules left empty."""
    from odwolania.pipeline import process_file

    processed = process_file(Path(pdf_path), mode="bielik")
    if document_type == "unknown":
        if not processed.document_type:
            return payload, document_type, {}
        sources: dict[str, str] = {}
        _tag(processed.data, sources, "llm", "")
        return processed.data, processed.document_type, sources
    if processed.document_type != document_type:
        return payload, document_type, tag_rules(payload)
    merged, sources = merge_payload(payload, processed.data, processed.sources)
    return merged, document_type, sources


def _fill(
    dest: dict,
    src: dict,
    sources: dict[str, str],
    prefix: str,
    incoming_sources: dict[str, str],
) -> None:
    for key, incoming in src.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in dest or _missing(dest.get(key)):
            if _missing(incoming):
                continue
            dest[key] = copy.deepcopy(incoming)
            sources.pop(path, None)
            _tag(dest[key], sources, "llm", path, incoming_sources)
            continue
        current = dest[key]
        if isinstance(current, dict) and isinstance(incoming, dict):
            _fill(current, incoming, sources, path, incoming_sources)
        elif isinstance(current, list) and isinstance(incoming, list):
            _fill_list(current, incoming, sources, path, incoming_sources)


def _fill_list(
    dest: list,
    src: list,
    sources: dict[str, str],
    prefix: str,
    incoming_sources: dict[str, str],
) -> None:
    if not dest and src:
        dest.extend(copy.deepcopy(src))
        _tag(dest, sources, "llm", prefix, incoming_sources)
        return
    for index, incoming in enumerate(src):
        if index >= len(dest):
            return
        path = f"{prefix}[{index}]"
        if _missing(dest[index]) and not _missing(incoming):
            dest[index] = copy.deepcopy(incoming)
            _tag(dest[index], sources, "llm", path, incoming_sources)
        elif isinstance(dest[index], dict) and isinstance(incoming, dict):
            _fill(dest[index], incoming, sources, path, incoming_sources)


def _tag(
    value: object,
    sources: dict[str, str],
    kind: str,
    prefix: str,
    incoming_sources: dict[str, str] | None = None,
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            _tag(item, sources, kind, path, incoming_sources)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _tag(item, sources, kind, f"{prefix}[{index}]", incoming_sources)
    elif prefix:
        sources[prefix] = _lookup(prefix, incoming_sources) or kind


def _lookup(path: str, incoming_sources: dict[str, str] | None) -> str | None:
    if not incoming_sources:
        return None
    if path in incoming_sources and incoming_sources[path] in ("rule", "llm"):
        return incoming_sources[path]
    leaf = path.rsplit(".", 1)[-1]
    found = incoming_sources.get(leaf)
    if found in ("rule", "llm"):
        return found
    return None


def _missing(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}

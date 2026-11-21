"""Classify a document from its text. Filename is never an input."""

from __future__ import annotations

import re
from dataclasses import dataclass

from odwolania.config import load_settings

_FLAGS = re.IGNORECASE | re.MULTILINE
_FOLD = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def _fold(text: str) -> str:
    return text.translate(_FOLD)


def _matches(pattern: str, text: str) -> bool:
    if re.search(pattern, text, _FLAGS):
        return True
    folded = _fold(pattern)
    if folded == pattern:
        return False
    return re.search(folded, _fold(text), _FLAGS) is not None


@dataclass(frozen=True)
class Classification:
    label: str | None
    scores: dict[str, float]


def classify(text: str) -> str | None:
    """Return a document type id, or None when the text is below threshold."""
    return classify_text(text).label


def classify_with_llm(text: str, client: object | None = None) -> str | None:
    """Ask the LLM to pick a configured type. Used only when rules return None."""
    from odwolania.llm import LLMClient

    settings = load_settings()
    allowed = [doc.id for doc in settings.document_types]
    prompt = (
        "Sklasyfikuj dokument wyłącznie na podstawie treści. "
        f"Dozwolone wartości type: {', '.join(allowed)}, albo null. "
        'Zwróć JSON {"type": "<id albo null>"}.'
    )
    llm = client if client is not None else LLMClient()
    raw = llm.extract_json(prompt, text or "")
    label = raw.get("type") if isinstance(raw, dict) else None
    if isinstance(label, str) and label in allowed:
        return label
    return None


def classify_text(text: str) -> Classification:
    settings = load_settings()
    if not text or not text.strip():
        return Classification(None, {doc.id: 0.0 for doc in settings.document_types})

    scores: dict[str, float] = {}
    for doc in settings.document_types:
        score = 0.0
        for keyword in doc.keywords:
            if _matches(keyword.pattern, text):
                score += keyword.weight
        scores[doc.id] = score

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_label, best_score = ranked[0]
    if best_score < settings.threshold:
        return Classification(None, scores)
    if len(ranked) > 1 and best_score - ranked[1][1] < settings.margin:
        return Classification(None, scores)
    return Classification(best_label, scores)

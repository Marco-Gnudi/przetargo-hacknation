"""Classify a document from its text. Filename is never an input."""

from __future__ import annotations

import re
from dataclasses import dataclass

from odwolania.config import load_settings

_FLAGS = re.IGNORECASE | re.MULTILINE


@dataclass(frozen=True)
class Classification:
    label: str | None
    scores: dict[str, float]


def classify(text: str) -> str | None:
    """Return a document type id, or None when the text is below threshold."""
    return classify_text(text).label


def classify_text(text: str) -> Classification:
    settings = load_settings()
    if not text or not text.strip():
        return Classification(None, {doc.id: 0.0 for doc in settings.document_types})

    scores: dict[str, float] = {}
    for doc in settings.document_types:
        score = 0.0
        for keyword in doc.keywords:
            if re.search(keyword.pattern, text, _FLAGS):
                score += keyword.weight
        scores[doc.id] = score

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_label, best_score = ranked[0]
    if best_score < settings.threshold:
        return Classification(None, scores)
    if len(ranked) > 1 and best_score - ranked[1][1] < settings.margin:
        return Classification(None, scores)
    return Classification(best_label, scores)

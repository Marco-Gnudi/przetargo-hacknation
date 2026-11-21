"""Classify a document from its text. Filename is never an input."""

from __future__ import annotations


def classify(text: str) -> str | None:
    """Return a document type id, or None when the text is not a known type.

    Stub: every document is unclassified, so the pipeline writes {}.
    """
    del text
    return None

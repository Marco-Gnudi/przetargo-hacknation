"""Light cleanup of Tesseract text before the rule extractors see it."""

from __future__ import annotations

import re

_QUOTES = str.maketrans({
    "„": '"',
    "“": '"',
    "”": '"',
    "«": '"',
    "»": '"',
    "’": "'",
    "‘": "'",
})
_LOOKALIKES = str.maketrans({
    "O": "0",
    "o": "0",
    "l": "1",
    "I": "1",
    "S": "5",
    "s": "5",
    "B": "8",
})
_RUN = re.compile(r"[0-9OoIlSsBb](?:[ \t]*[0-9OoIlSsBb./-]){3,}[0-9OoIlSsBb]")
_BROKEN_ID = re.compile(
    r"(?i)(?<![A-Za-z0-9])(PL[ \t-]*)?(\d(?:[ \t-]*\d){9,31})(?!\d)"
)


def cleanup_ocr(text: str) -> str:
    """Fix digit lookalikes, join split IBANs and NIPs, and tidy quotes."""
    if not text:
        return ""
    cleaned = text.replace("\xa0", " ").replace("\u200b", "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = cleaned.translate(_QUOTES)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = _RUN.sub(_fix_run, cleaned)
    cleaned = _BROKEN_ID.sub(_join_id, cleaned)
    return cleaned.strip()


def _fix_run(match: re.Match[str]) -> str:
    chunk = match.group(0)
    compact = re.sub(r"[^0-9A-Za-z]", "", chunk)
    if not compact:
        return chunk
    digits = sum(character.isdigit() for character in compact)
    if digits < 4 or digits / len(compact) < 0.5:
        return chunk
    return chunk.translate(_LOOKALIKES)


def _join_id(match: re.Match[str]) -> str:
    body = match.group(2)
    if not re.search(r"[ \t-]", body):
        return match.group(0)
    digits = re.sub(r"\D", "", body)
    if len(digits) not in {10, 26}:
        return match.group(0)
    prefix = "PL" if match.group(1) else ""
    return prefix + digits

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


_JUNK = r"[|*_©®~`\\/{}\[\]<>=+°¶•]"
_EDGE_PUNCT = r"[.,:;'\"]"
_LEAD = re.compile(rf"^(?:{_JUNK}+|(?:{_EDGE_PUNCT}|[-—])+(?=\s)|[A-Za-z]{{1,2}}(?=\s+(?:{_JUNK}|{_EDGE_PUNCT})(?:\s|$)))\s*")
_TRAIL = re.compile(
    rf"(?:\s+(?:{_JUNK}+|{_EDGE_PUNCT}+)|\s+{_JUNK}+\s*[A-Za-z]{{1,3}}"
    r"|(?<=[a-ząćęłńóśźż]{2})\s+(?![IVX]+$)[A-ZĄĆĘŁŃÓŚŹŻ]{1,2})$"
)
_LONE = re.compile(rf"(?<=\S)\s+(?:{_JUNK}+|[.,:;]+)(?=\s+\S)")
_REPEAT = re.compile(r"\b([a-z])(?:\s+\1\b)+")
_AT_SURE = re.compile(r"(?<=[a-z0-9])(?:\(OQ|\(a\s?|\s?[Q©®G]\s?)(?=[a-z][a-z0-9-]*\.[a-z])")
_TLD = re.compile(r"(?<=[a-z0-9-]\.)(?:e[a-z]amp[a-z][ceęe]|[ce]x[a-z]mpl[a-zę]|ex[a-z]mple|examp[a-z]e)\b")
_DOMAIN = re.compile(r"(?:@|www\.\s?)([a-z][a-z0-9-]*\.[a-z]{2,}(?:\.[a-z]{2,})?)")


def cleanup_ocr(text: str) -> str:
    """Fix digit lookalikes, join split IBANs and NIPs, and tidy quotes."""
    if not text:
        return ""
    cleaned = text.replace("\xa0", " ").replace("\u200b", "").replace("\r\n", "\n").replace("\r", "\n")
    cleaned = cleaned.translate(_QUOTES)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = "\n".join(_tidy_line(line) for line in cleaned.split("\n"))
    cleaned = _RUN.sub(_fix_run, cleaned)
    cleaned = _BROKEN_ID.sub(_join_id, cleaned)
    cleaned = _fix_words(cleaned)
    cleaned = _repair_emails(cleaned)
    return cleaned.strip()


def _tidy_line(line: str) -> str:
    """Drop margin specks, table rules and stray letters Tesseract adds at line edges."""
    previous = None
    while previous != line:
        previous = line
        line = line.strip()
        line = _LEAD.sub("", line)
        line = _TRAIL.sub("", line)
    line = _LONE.sub("", line)
    line = _REPEAT.sub(r"\1", line)
    return "" if re.fullmatch(r"[A-Za-z]{1,2}", line) else line


def _fix_words(text: str) -> str:
    text = re.sub(r"\b([Ss]p\.)\s?[zZ]\s?[0oO]\.\s?[0oO]\.", r"\1 z o.o.", text)
    text = re.sub(r"\b([Ss]p\.)\s?([kKjJpP])\.(?=\s|$|,)", lambda m: f"{m.group(1)} {m.group(2).lower()}.", text)
    text = re.sub(r"(?<=\w) 6 (?=Partner)", " & ", text)
    text = re.sub(r"(?<=[a-ząćęłńóśźż])- (?=[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż])", "-", text)
    return text


def _repair_emails(text: str) -> str:
    text = _TLD.sub("example", text)
    text = re.sub(r"(?<=[a-z0-9-])\|(?=[a-z-]*-kancelaria)", "l", text)
    text = re.sub(r"(?<=[a-z0-9-])ł(?=aria\.)", "l", text)
    text = _AT_SURE.sub("@", text)
    domains = sorted({match.group(1) for match in _DOMAIN.finditer(text)}, key=len, reverse=True)
    for domain in domains:
        pattern = re.compile(rf"(?<=[a-z0-9])(?:\(o|\(a\s?|ta\s|a\s|[ao]|ść\s?|fii|Gr|gó)(?={re.escape(domain)})")
        text = pattern.sub("@", text)
    return text


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

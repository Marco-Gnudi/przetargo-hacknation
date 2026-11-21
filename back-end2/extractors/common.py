"""Shared section helpers for the specialized extractors."""

import re

from normalizers import compact, email, identifier


def section(text, start, end):
    match = re.search(start, text, re.IGNORECASE)
    if not match:
        return ""
    rest = text[match.end():]
    end_match = re.search(end, rest, re.IGNORECASE)
    body = rest[: end_match.start()] if end_match else rest[:2500]
    return body.strip()


def party_name(block):
    chunks = split_numbered(block)
    if len(chunks) > 1:
        block = chunks[0]
    lines = [compact(line) for line in block.splitlines() if compact(line)]
    skipped = re.compile(
        r"^(?:odwo[łl]uj[aą]c\w*|zamawiaj[aą]c\w*|mocodawc\w*|pe[łl]nomocni\w*|\d+\)|ul\.|krs\b|nip\b|regon\b|tel\.|e-?mail\b|kontakt\b|adres\b|reprezentowan|przedsi[eę]biorca\b|wpisan\w*|prowadz[aą]c)",
        re.IGNORECASE,
    )
    for line in lines:
        if "@" in line or not re.search(r"[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]", line):
            continue
        if skipped.match(line):
            continue
        if re.match(r"^(?:lider|partner|konsorcjum)\b", line, re.IGNORECASE) and not re.search(
            r"\b(?:s\.a\.|sp\.)", line, re.IGNORECASE
        ):
            continue
        if re.search(r"art\.\s*\d+", line, re.IGNORECASE):
            continue
        name = re.split(r"\bul\.|\bKRS\b|\bNIP\b|\bREGON\b", line, maxsplit=1, flags=re.IGNORECASE)[0]
        name = name.strip(" ,;:-*'\"›")
        if len(name) < 3:
            continue
        return name
    return None


def party_ids(block):
    return {
        "krs": _labeled(block, "KRS", (9, 10, 14)),
        "nip": _labeled(block, "NIP", (10,)),
        "regon": _labeled(block, "REGON", (9, 14)),
    }


def _labeled(block, label, lengths):
    match = re.search(rf"{label}\D{{0,15}}(\d[\d \-]{{8,20}})", block, re.IGNORECASE)
    if not match:
        return None
    return identifier(match.group(1), lengths)


def party_email(block):
    return email(block)


def split_numbered(block):
    parts = re.split(r"(?:^|\n)\s*\d+\)\s*", block)
    parts = [part.strip() for part in parts if part.strip()]
    if len(parts) <= 1:
        return [block]
    # The preamble before "1)" is not a party.
    if not re.search(r"\bKRS\b|\bNIP\b", parts[0], re.IGNORECASE):
        return parts[1:]
    return parts

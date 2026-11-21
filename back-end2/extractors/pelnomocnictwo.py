"""Extract a power of attorney."""

import re

from checksums import repair_nip, repair_pesel
from extractors.common import party_ids
from normalizers import compact, person_name


def extract_pelnomocnictwo(document, rules):
    text = document.text
    flat = document.flat
    ocr = document.text_source == "ocr"
    principals = _principals(text, flat, ocr)
    agents = _agents(flat, ocr)
    if not agents:
        agents = [{"imie_nazwisko": None, "pesel": None}]
    return {"mocodawca": principals, "pelnomocnicy": agents}


def _principals(text, flat, ocr=False):
    if re.search(r"prowadząc\w*\s+działalność|pod firmą", flat, re.IGNORECASE):
        return [_natural_person(flat, ocr)]
    block = _principal_block(text)
    ids = _checked_nip(party_ids(text), ocr)
    name = _legal_name(text)
    signatories = _signatories(text)
    return [{
        "data": {
            "imie_nazwisko": None,
            "krs": ids["krs"],
            "nazwa": name,
            "nip": ids["nip"],
            "typ": "osoba_prawna" if ids["krs"] or _looks_like_company(name) else "osoba_fizyczna",
        },
        "podpisujacy": signatories or [{"imie_nazwisko": None}],
    }]


def _natural_person(flat, ocr=False):
    person = None
    match = re.search(r"niżej podpisan\w+\s+([A-ZĄĆĘŁŃÓŚŹŻ][^,]{2,80}),", flat)
    if match:
        person = person_name(match.group(1))
    firm = None
    firm_match = re.search(r"pod firmą\s+(.+?)(?:,|\s+ul\.)", flat, re.IGNORECASE)
    if firm_match:
        firm = compact(firm_match.group(1))
    ids = _checked_nip(party_ids(flat), ocr)
    return {
        "data": {
            "imie_nazwisko": person,
            "krs": None,
            "nazwa": firm,
            "nip": ids["nip"],
            "typ": "osoba_fizyczna",
        },
        "podpisujacy": [{"imie_nazwisko": person}],
    }


def _principal_block(text):
    match = re.search(
        r"(?:§\s*1\.?\s*Mocodawca|Mocodawc[aą]\s*(?:jest|:)?)",
        text,
        re.IGNORECASE,
    )
    if not match:
        return ""
    rest = text[match.start():]
    end = re.search(r"\n\s*§\s*2|\n\s*Pe[łl]nomocni|\n\s*Mocodawca ustanaw", rest, re.IGNORECASE)
    return rest[: end.start()] if end else rest[:800]


def _legal_name(block):
    flat = compact(block)
    match = re.search(r"Mocodawc[aą]\s+jest\s+(.+?)(?:,|\s+ul\.)", flat, re.IGNORECASE)
    if match:
        return _without_heading(compact(match.group(1)))
    pattern = re.compile(
        r"([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż.&'-]*(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż.&'-]*){0,6}\s+"
        r"(?:S\.A\.|sp\.\s*z\s*o\.o\.(?:\s*sp\.\s*k\.)?|sp\.\s*k\.|sp\.\s*j\.))",
    )
    for found in pattern.finditer(flat):
        name = compact(found.group(1))
        name = re.sub(r"^.*\b(?:imieniu|Pe[łl]nomocnictwo(?:\s*procesowe)?)\s+", "", name, flags=re.IGNORECASE)
        name = _without_heading(name)
        if re.search(r"\b(?:S\.A\.|sp\.)", name):
            return name.strip(" ,;")
    return None


def _without_heading(name):
    cleaned = re.sub(
        r"^(?:mocodawca|pełnomocnik|pełnomocnictwo)\b\s*",
        "",
        name,
        flags=re.IGNORECASE,
    )
    return cleaned.strip(" ,;:")


def _signatories(text):
    names = _people_after(
        text,
        r"reprezentowan\w+\s+przez\s*:?\s*(.+?)(?:\(dalej|niniejszym|,\s*\d+\)|\n\s*\d+\))",
    )
    if names:
        return [{"imie_nazwisko": name} for name in names]
    names = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        cleaned = compact(line).strip(" ._")
        if not _role_line(cleaned) or index == 0:
            continue
        name = person_name(compact(lines[index - 1]).strip(" ._"))
        if name and name not in names:
            names.append(name)
    if names:
        return [{"imie_nazwisko": name} for name in names]
    match = re.search(r"Mocodawca\s*:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    for line in match.group(1).splitlines():
        cleaned = compact(line).strip(" ._")
        if _role_line(cleaned):
            continue
        name = person_name(cleaned)
        if name and name not in names:
            names.append(name)
        if names:
            break
    return [{"imie_nazwisko": name} for name in names]


def _checked_nip(ids, ocr):
    if ocr and ids.get("nip"):
        ids = dict(ids)
        ids["nip"] = repair_nip(ids["nip"])
    return ids


def _agents(flat, ocr=False):
    found = []
    pattern = re.compile(
        r"(?i:r\.\s*pr\.|adw\.|radc[aą]\s+prawn\w+|adwokat)\s+"
        r"([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż'-]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż'-]+){1,2})"
    )
    for name_match in pattern.finditer(flat):
        name = _as_person(name_match.group(1))
        if name and name not in found:
            found.append(name)
    if not found:
        found = _people_after(
            flat,
            r"udziela.{0,12}pe[łl]nomocnictwa\s*:?\s*(.+?)(?:\bdo\s+reprezent|\(dalej\b|$)",
        )
    pesel = _pesel(flat, ocr)
    agents = [{"imie_nazwisko": name, "pesel": pesel if index == 0 else None} for index, name in enumerate(found)]
    return agents


_PAIR = re.compile(
    r"\b([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż'-]{1,})\s+([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż'-]{1,})"
)
_NOT_A_NAME = re.compile(
    r"^(?:mocodawca|pełnomocnik|pełnomocnictwo|prezes|wiceprezes|członek|prokurent|zarząd|adwokat|radca|rejestru|konsorcjum|budownictwo|sądowego|partner|lider)$",
    re.IGNORECASE,
)


def _people_after(text, pattern):
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    chunk = re.split(r"\s+[—–-]\s+|\(", match.group(1))[0]
    names = []
    for first, last in _PAIR.findall(match.group(1)):
        if _NOT_A_NAME.match(first) or _NOT_A_NAME.match(last):
            continue
        name = _as_person(f"{first} {last}")
        if name and name not in names:
            names.append(name)
    if names:
        return names
    name = _as_person(chunk)
    return [name] if name else []


def _as_person(value):
    name = person_name(value)
    if not name:
        return None
    if name.isupper():
        return name.title()
    return name


def _pesel(flat, ocr=False):
    match = re.search(r"PESEL\s*[:.]?\s*([0-9OIlSBZG]{11})", flat, re.IGNORECASE)
    if not match:
        return None
    if ocr:
        return repair_pesel(match.group(1))
    digits = re.sub(r"\D", "", match.group(1))
    return digits if len(digits) == 11 else None


def _role_line(line):
    return bool(re.match(
        r"^(?:prezes|wiceprezes|członek|prokurent|dyrektor|wicedyrektor|zarząd)\b",
        line,
        re.IGNORECASE,
    ))


def _looks_like_company(name):
    if not name:
        return False
    return bool(re.search(r"\b(?:s\.a\.|sp\.|spółka|spółdziel)", name, re.IGNORECASE))

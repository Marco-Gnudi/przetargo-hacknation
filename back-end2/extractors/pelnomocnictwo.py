"""Extract a power of attorney."""

import re

from extractors.common import party_ids
from normalizers import compact, person_name


def extract_pelnomocnictwo(document, rules):
    text = document.text
    flat = document.flat
    principals = _principals(text, flat)
    agents = _agents(flat)
    if not agents:
        agents = [{"imie_nazwisko": None, "pesel": None}]
    return {"mocodawca": principals, "pelnomocnicy": agents}


def _principals(text, flat):
    if re.search(r"prowadząc\w*\s+działalność|pod firmą", flat, re.IGNORECASE):
        return [_natural_person(flat)]
    block = _principal_block(text)
    ids = party_ids(text)
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


def _natural_person(flat):
    person = None
    match = re.search(r"niżej podpisan\w+\s+([A-ZĄĆĘŁŃÓŚŹŻ][^,]{2,80}),", flat)
    if match:
        person = person_name(match.group(1))
    firm = None
    firm_match = re.search(r"pod firmą\s+(.+?)(?:,|\s+ul\.)", flat, re.IGNORECASE)
    if firm_match:
        firm = compact(firm_match.group(1))
    ids = party_ids(flat)
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
    end = re.search(r"\n\s*§\s*2|\n\s*Pełnomocni|\n\s*Mocodawca ustanaw", rest, re.IGNORECASE)
    return rest[: end.start()] if end else rest[:800]


def _legal_name(block):
    flat = compact(block)
    match = re.search(r"Mocodawc[aą]\s+jest\s+(.+?)(?:,|\s+ul\.)", flat, re.IGNORECASE)
    if match:
        return compact(match.group(1))
    pattern = re.compile(
        r"([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż.&'-]*(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż.&'-]*){0,6}\s+"
        r"(?:S\.A\.|sp\.\s*z\s*o\.o\.(?:\s*sp\.\s*k\.)?|sp\.\s*k\.|sp\.\s*j\.))",
    )
    for found in pattern.finditer(flat):
        name = compact(found.group(1))
        name = re.sub(r"^.*\b(?:imieniu|Pełnomocnictwo(?:\s+procesowe)?)\s+", "", name, flags=re.IGNORECASE)
        if re.search(r"\b(?:S\.A\.|sp\.)", name):
            return name.strip(" ,;")
    return None


def _signatories(text):
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


def _agents(flat):
    window = flat
    match = re.search(
        r"(?:pełnomocnik(?:iem|a|ów)?|pełnomocnictwa)\s*[:,]?\s*(.+?)(?:pełnomocnictwo dotyczy|pełnomocnictwo udzielone|zakres|§\s*3|$)",
        flat,
        re.IGNORECASE,
    )
    if match:
        window = match.group(1)
    found = []
    pattern = re.compile(
        r"(?:r\.\s*pr\.|adw\.|radca prawny|adwokat)\s+([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż-]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż-]+){1,2})",
        re.IGNORECASE,
    )
    for name_match in pattern.finditer(window):
        name = person_name(name_match.group(1))
        if name and name not in found:
            found.append(name)
    pesel = _pesel(flat)
    agents = [{"imie_nazwisko": name, "pesel": pesel if index == 0 else None} for index, name in enumerate(found)]
    return agents


def _pesel(flat):
    match = re.search(r"PESEL\s*[:.]?\s*(\d{11})", flat, re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


def _role_line(line):
    return bool(re.match(r"^(?:prezes|wiceprezes|członek|prokurent|zarząd)", line, re.IGNORECASE))


def _looks_like_company(name):
    if not name:
        return False
    return bool(re.search(r"\b(?:s\.a\.|sp\.|spółka|spółdziel)", name, re.IGNORECASE))

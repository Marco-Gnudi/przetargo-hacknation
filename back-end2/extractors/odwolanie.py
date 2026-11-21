"""Extract a KIO appeal into the organizer schema."""

import re

from extractors.common import party_email, party_ids, party_name, section, split_numbered
from normalizers import bzp_number, compact, parse_date, person_name, ted_number


def extract_odwolanie(document, rules):
    text = document.text
    flat = document.flat
    party_end = (
        r"\n\s*(?:Odwołując\w*\s*:|Zamawiając\w*\s*:|Wykonawca wybrany\b|dotyczy\s*:|ODWOŁANIE\b)"
    )
    appellant_block = section(text, r"Odwołując\w*\s*:", party_end)
    authority_block = section(text, r"Zamawiając\w*\s*(?:\(|:)", party_end)
    procurement = _procurement_window(flat)
    act = _act_window(flat)
    powod_id, powod_opis = _powod(act, rules["powod"])
    city, appeal_date = _header_place_date(text)
    return {
        "OdwolanieKIO": {
            "data": appeal_date,
            "czynnosc_dzien": _act_date(act),
            "czynnosc_powod_id": powod_id,
            "czynnosc_opis": powod_opis,
            "miejscowosc": city,
        },
        "Odwolujacy": [_appellant(appellant_block)],
        "Zamawiajacy": _authorities(authority_block),
        "ZamowieniePubliczne": {
            "numer_bzp": bzp_number(procurement),
            "numer_postepowania": _reference(procurement),
            "numer_ted": ted_number(procurement),
            "tytul": _title(procurement),
        },
    }


def _appellant(block):
    ids = party_ids(block)
    representative = _representative(block)
    return {
        "krs": ids["krs"],
        "nazwa": party_name(block),
        "nip": ids["nip"],
        "regon": ids["regon"],
        "przez-pelnomocnika": 1 if representative["imie_nazwisko"] or representative["nazwa"] else 0,
        "pelnomocnik": representative,
    }


def _representative(block):
    name = None
    match = re.search(
        r"reprezentowan\w+\s+przez\s*:\s*(.+?)(?:\n|adres do korespondencji)",
        block,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        first = re.split(r",|\si\s", match.group(1))[0]
        name = person_name(first)
    firm = None
    mail = None
    address = re.search(
        r"adres do korespondencji\s*:\s*(.+?),\s*ul\.",
        compact(block),
        re.IGNORECASE,
    )
    if address:
        firm = address.group(1).strip()
    mail = party_email(block)
    return {"imie_nazwisko": name, "nazwa": firm, "mail": mail}


def _authorities(block):
    chunks = split_numbered(block)
    multiple = len(chunks) > 1
    parties = []
    for chunk in chunks:
        ids = party_ids(chunk)
        parties.append({
            "krs": ids["krs"],
            "nazwa": party_name(chunk),
            "nip": ids["nip"],
            "regon": ids["regon"],
            "prowadzacy_postepowanie": _leader_flag(chunk, multiple),
        })
    return parties or [{
        "krs": None,
        "nazwa": None,
        "nip": None,
        "regon": None,
        "prowadzacy_postepowanie": None,
    }]


def _leader_flag(chunk, multiple):
    if not multiple:
        return None
    if re.search(r"lider|prowadząc", chunk, re.IGNORECASE):
        return 1
    return 0


def _procurement_window(flat):
    match = re.search(r"(?:dotyczy\s*:|pn\.).{0,900}", flat, re.IGNORECASE)
    return match.group(0) if match else flat


def _title(window):
    match = re.search(r"[„\"](.+?)[”\"]", window)
    if not match:
        return None
    return compact(match.group(1))


def _reference(window):
    match = re.search(
        r"(?:nr referencyjny(?:\s+sprawy)?|numer postępowania|nr postępowania)\s*[:.]?\s*([A-Z0-9][A-Z0-9./-]*)",
        window,
        re.IGNORECASE,
    )
    return match.group(1).rstrip(".,;") if match else None


def _act_date(act):
    match = re.search(r"w dniu\s+(.{6,40}?\d{4})", act, re.IGNORECASE)
    if not match:
        return None
    return parse_date(match.group(1))


def _act_window(flat):
    match = re.search(r"(.{0,500})\s+zarzut\s+nr\s*1\b", flat, re.IGNORECASE)
    return match.group(1) if match else ""


def _header_place_date(text):
    match = re.search(
        r"([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż-]+),\s*(?:dnia\s+)?(\d{1,2}(?:[./-]\d{1,2}[./-]\d{4}|\s+[A-Za-ząćęłńóśźż]+\s+\d{4}))",
        text,
    )
    if not match:
        return None, None
    return match.group(1), parse_date(match.group(2))


def _powod(act, rules):
    lowered = act.lower()
    for rule in rules:
        if re.search(rule["pattern"], lowered, re.IGNORECASE):
            return rule["id"], rule["opis"]
    return None, None

"""Extract a KIO appeal into the organizer schema."""

import re

from checksums import repair_nip, repair_regon
from extractors.common import party_email, party_ids, party_name, section, split_numbered
from normalizers import bzp_number, compact, parse_date, person_name, ted_number


def extract_odwolanie(document, rules):
    text = document.text
    flat = document.flat
    party_end = (
        r"\n\s*(?:Odwo[łl]uj[aą]c\w*\s*:|Zamawiaj[aą]c\w*\s*:|Wykonawca wybrany\b|dotyczy\s*:|ODWO[ŁL]ANIE\b)"
    )
    appellant_block = section(text, r"Odwo[łl]uj[aą]c\w*\s*:", party_end)
    authority_block = section(text, r"Zamawiaj[aą]c\w*\s*(?:\(|:)", party_end)
    procurement = _procurement_window(flat)
    act = _act_window(flat)
    powod_id, powod_opis = _powod(act, rules["powod"])
    city, appeal_date = _header_place_date(text)
    return {
        "OdwolanieKIO": {
            "data": appeal_date,
            "czynnosc_dzien": _act_date(act, flat),
            "czynnosc_powod_id": powod_id,
            "czynnosc_opis": powod_opis,
            "miejscowosc": city,
        },
        "Odwolujacy": [_appellant(appellant_block, document.text_source == "ocr")],
        "Zamawiajacy": _authorities(authority_block, document.text_source == "ocr"),
        "ZamowieniePubliczne": {
            "numer_bzp": bzp_number(procurement),
            "numer_postepowania": _reference(procurement),
            "numer_ted": ted_number(procurement),
            "tytul": _title(procurement),
        },
    }


def _appellant(block, ocr=False):
    ids = _checked(party_ids(block), ocr)
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
        r"reprezentowan\w+\s+przez(?:\s+pe[łl]\w{3,7}ika)?\s*:\s*(.+?)(?:\n|adres do korespondencji)",
        block,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        body = re.sub(
            r"^(?:radc[aą]\s+prawn\w+|adwokat|adw\.|r\.\s*pr\.)\s+",
            "",
            compact(match.group(1)),
            count=1,
            flags=re.IGNORECASE,
        )
        first = re.split(
            r",|\s+i\s+|\bradc[aą]\s+prawn|\badw(?:okat)?\.",
            body,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        name = person_name(first)
    firm = None
    address = re.search(
        r"adres do korespondencji\s*:\s*(.+?)(?:,\s*|\s+)ul\.",
        compact(block),
        re.IGNORECASE,
    )
    if address:
        firm = address.group(1).strip()
    if not firm:
        firm = _law_firm(block)
    return {"imie_nazwisko": name, "nazwa": firm, "mail": party_email(block)}


def _law_firm(block):
    match = re.search(
        r"((?:kancelaria\s+radcy\s+prawnego|kancelaria\s+adwokacka)\s+.{5,70}?)(?:\s+ul\b|,|\s+tel\b)",
        compact(block),
        re.IGNORECASE,
    )
    if not match:
        return None
    firm = match.group(1).strip(" ,.;'\"")
    return firm.title() if firm.isupper() else firm


def _authorities(block, ocr=False):
    chunks = split_numbered(block)
    multiple = len(chunks) > 1
    parties = []
    for chunk in chunks:
        ids = _checked(party_ids(chunk), ocr)
        parties.append({
            "krs": ids["krs"],
            "nazwa": _authority_name(chunk),
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


def _checked(ids, ocr):
    if not ocr:
        return ids
    return {
        "krs": ids["krs"],
        "nip": repair_nip(ids["nip"]) if ids["nip"] else None,
        "regon": repair_regon(ids["regon"]) if ids["regon"] else None,
    }


def _authority_name(chunk):
    name = party_name(chunk)
    if not name:
        preamble = re.split(r"(?:^|\n)\s*\d+\)\s*", chunk, maxsplit=1)[0]
        name = party_name(preamble)
    if name:
        return name
    match = re.search(
        r"zamawiaj\w*\s*:\s*[\s'\"\.]*([A-ZĄĆĘŁŃÓŚŹŻ].{8,160}?)(?:\s+ul\b|\s+\d{2}-\d{3}\b)",
        compact(chunk),
        re.IGNORECASE,
    )
    if not match:
        return None
    return compact(match.group(1)).strip(" '\".,")


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


def _act_date(act, flat=""):
    for source, pattern in (
        (act, r"w dniu\s+(.{6,40}?\d{4})"),
        (act, r"pismem\s+z\s+(?:dnia\s+)?(.{6,30}?\d{4})"),
        (flat, r"przekazan\w*\s+Odwo[łl]uj\w*\s+w dniu\s+(.{6,30}?\d{4})"),
    ):
        match = re.search(pattern, source, re.IGNORECASE)
        if match and parse_date(match.group(1)):
            return parse_date(match.group(1))
    return None


def _act_window(flat):
    """Text PDFs put the act just before "zarzut nr 1". Scans bury that heading."""
    match = re.search(r"(.{0,500})\s+zarzut\s+nr\s*1\b", flat, re.IGNORECASE)
    if match:
        return match.group(1)
    filed = re.search(
        r"wnosz\w*\s+odwo[łl]an\w+\s+(.{0,700})",
        flat,
        re.IGNORECASE,
    )
    if filed:
        return filed.group(1)
    later = re.search(r"(.{0,900})\s+zarzut\w*\s+nr\s*[1lI]\b", flat, re.IGNORECASE)
    return later.group(1) if later else ""


def _header_place_date(text):
    date = r"(?:dnia\s+)?(\d{1,2}(?:[./-]\d{1,2}[./-]\d{4}|\s+[A-Za-ząćęłńóśźż]+\s+\d{4}))"
    match = re.search(rf"([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż-]+),\s*{date}", text)
    if not match:
        match = re.search(rf"(?m)^([A-ZĄĆĘŁŃÓŚŹŻ][\wąćęłńóśźż-]+)\s+{date}", text[:300])
    if not match:
        return None, None
    return match.group(1), parse_date(match.group(2))


def _powod(act, rules):
    lowered = act.lower()
    for rule in rules:
        if re.search(rule["pattern"], lowered, re.IGNORECASE):
            return rule["id"], rule["opis"]
    return None, None

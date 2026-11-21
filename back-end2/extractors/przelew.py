"""Extract a bank-transfer confirmation from labeled lines."""

import re

from checksums import repair_nrb
from normalizers import account_number, amount, parse_date, transaction_id, compact


def extract_przelew(document, rules):
    labels = [(item["field"], re.compile(item["pattern"], re.IGNORECASE)) for item in rules["transfer_labels"]]
    stop = re.compile(rules["transfer_stop"], re.IGNORECASE)
    captured = {field: [] for field, _ in labels}
    current = None
    for raw_line in _lines(document.text):
        if stop.match(raw_line):
            current = None
            continue
        field = _match_label(raw_line, labels)
        if field:
            current = field
            continue
        if current:
            captured[current].append(raw_line)
    values = {field: compact(" ".join(lines)) for field, lines in captured.items()}
    payload = {
        "przelew_bankowy": {
            "data_operacji": parse_date(values.get("data_operacji")),
            "kwota": amount(values.get("kwota")),
            "na_rachunek": account_number(values.get("na_rachunek")),
            "numer_transakcji": transaction_id(values.get("numer_transakcji")),
            "tytul": _trim_title(values.get("tytul")),
            "z_rachunku": account_number(values.get("z_rachunku")),
        }
    }
    return _fill_gaps(document, payload)


def _lines(text):
    prepared = re.sub(r"\.{3,}", "\n", text)
    rows = []
    for raw in prepared.splitlines():
        line = compact(raw).rstrip(".")
        if not line:
            continue
        split = re.match(r"^([^:]{3,50}):\s*(.+)$", line)
        if split and not split.group(1).lower().startswith("http"):
            rows.append(split.group(1).strip())
            rows.append(split.group(2).strip())
        else:
            rows.append(line)
    return rows


def _fill_gaps(document, payload):
    text = document.text
    ocr = getattr(document, "text_source", "text") == "ocr"
    transfer = payload["przelew_bankowy"]
    accounts = []
    for match in re.finditer(r"(?:PL[\s-]*)?((?:\d[\s-]*){26})", text, re.IGNORECASE):
        number = re.sub(r"\D", "", match.group(1))
        if len(number) == 26 and number not in accounts:
            accounts.append(number)
    checked = []
    for number in accounts:
        repaired = repair_nrb(number)
        if repaired and repaired not in checked:
            checked.append(repaired)
    if not checked and ocr:
        for match in re.finditer(r"(?i)(?:PL[\s-]*)?[0-9OIlSBZG][0-9OIlSBZG\s-]{18,40}", text):
            repaired = repair_nrb(match.group(0))
            if repaired and repaired not in checked:
                checked.append(repaired)
    accounts = checked or accounts
    if transfer["z_rachunku"]:
        transfer["z_rachunku"] = repair_nrb(transfer["z_rachunku"]) or (None if ocr else transfer["z_rachunku"])
    if transfer["na_rachunek"]:
        transfer["na_rachunek"] = repair_nrb(transfer["na_rachunek"]) or (None if ocr else transfer["na_rachunek"])
    if transfer["z_rachunku"] is None and accounts:
        transfer["z_rachunku"] = accounts[0]
    if transfer["na_rachunek"] is None and len(accounts) > 1:
        transfer["na_rachunek"] = accounts[1]
    if transfer["numer_transakcji"] is None:
        transfer["numer_transakcji"] = _repeated_id(text) or transaction_id(text)
    if transfer["tytul"] is None:
        title = re.search(r"szczeg\S{1,3}y\s+p\S{1,3}atno\S{1,4}\s*:?\s*(.{10,240})", compact(text), re.IGNORECASE)
        title = title or re.search(r"((?:op[łl]ata\s*skarbowa|tytu[łl]).{10,240})", compact(text), re.IGNORECASE)
        if title:
            transfer["tytul"] = _trim_title(compact(title.group(1)))
    if transfer["kwota"] is None:
        match = re.search(
            r"(?:kwocie|kwot[eę]|kwoty|kwota).{0,160}?(-?\d[\d\s]*[.,]\d{2})",
            compact(text),
            re.IGNORECASE,
        )
        if not match and ocr:
            match = re.search(r"(?<![\d.,])(\d[\d ]*[.,]\d{2})\s*PLN\b", text)
        if match:
            transfer["kwota"] = amount(match.group(1))
    if transfer["data_operacji"] is None:
        transfer["data_operacji"] = _operation_date(text) or _first_date(text)
    return payload


def _repeated_id(text):
    """Banks repeat the reference in the title; a token seen twice is rarely OCR noise."""
    tokens = re.findall(r"\b(?!PL\d{26}\b)([A-Z]{2,}[A-Z0-9]*\d{6,})\b", text)
    for token in tokens:
        if tokens.count(token) > 1:
            return token
    return None


def _operation_date(text):
    match = re.search(r"w dniu\s+(.{6,32}?)(?:\s+z\b|,)", text, re.IGNORECASE)
    if not match:
        return None
    return parse_date(match.group(1))


def _first_date(text):
    for line in text.splitlines():
        if re.search(r"wydruk|wygenerow", line, re.IGNORECASE):
            continue
        parsed = parse_date(line)
        if parsed:
            return parsed
    return None


def _trim_title(value):
    if not value:
        return None
    trimmed = re.sub(r"^(?:tytu[łl](?:em)?\s*[:łl]?\s*)+", "", value, flags=re.IGNORECASE)
    trimmed = re.sub(r"^(?:em|i|e)\s+(?=\S{3})", "", trimmed)
    trimmed = re.split(
        r"\b(?:dokument\s+jest\s+wydrukiem|typ\s*transakcji|strona\s*\d|s\S?gnature|dokument\s+podpisan\w*|typ\s*operacji|kana[łl]|potwierdzenie ma charakter|bank nie ponosi|status|numer\s*referencyjny|numer\s*transakcji|nr\s*ref\.?|waluta|tryb|data\s*(?:wygenerowania|transakcji|operacji)|kwota|z\s*powa[żz]aniem)\b",
        trimmed,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    trimmed = trimmed.strip(" „”\"'`“”")
    return compact(trimmed).strip(" ,.;") or None


def _match_label(line, labels):
    probe = line.lower().rstrip(":").strip()
    for field, pattern in labels:
        if pattern.match(probe):
            return field
    return None

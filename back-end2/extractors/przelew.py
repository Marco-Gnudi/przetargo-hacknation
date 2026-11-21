"""Extract a bank-transfer confirmation from labeled lines."""

import re

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
    return _fill_gaps(document.text, payload)


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


def _fill_gaps(text, payload):
    transfer = payload["przelew_bankowy"]
    accounts = []
    for match in re.finditer(r"(?:PL[\s-]*)?((?:\d[\s-]*){26})", text, re.IGNORECASE):
        number = re.sub(r"\D", "", match.group(1))
        if len(number) == 26 and number not in accounts:
            accounts.append(number)
    if transfer["z_rachunku"] is None and accounts:
        transfer["z_rachunku"] = accounts[0]
    if transfer["na_rachunek"] is None and len(accounts) > 1:
        transfer["na_rachunek"] = accounts[1]
    if transfer["numer_transakcji"] is None:
        transfer["numer_transakcji"] = transaction_id(text)
    if transfer["tytul"] is None:
        title = re.search(r"((?:opłata skarbowa|tytuł).{10,240})", compact(text), re.IGNORECASE)
        if title:
            transfer["tytul"] = _trim_title(compact(title.group(1)))
    if transfer["kwota"] is None:
        match = re.search(
            r"(?:kwocie|kwotę|kwoty|kwota)\s+(\d[\d\s]*[.,]\d{2})",
            text,
            re.IGNORECASE,
        )
        if match:
            transfer["kwota"] = amount(match.group(1))
    if transfer["data_operacji"] is None:
        transfer["data_operacji"] = _operation_date(text) or _first_date(text)
    return payload


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
    trimmed = re.split(
        r"\b(?:typ operacji|kanał|potwierdzenie ma charakter|bank nie ponosi|status|numer referencyjny|numer transakcji|nr ref\.?|waluta|tryb|data wygenerowania|z poważaniem)\b",
        value,
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

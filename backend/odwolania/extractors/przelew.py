"""Rule extractor for potwierdzenie przelewu. Unfilled fields go to the LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass

from odwolania.llm import LLMClient

FIELDS = (
    "data_operacji",
    "kwota",
    "na_rachunek",
    "numer_transakcji",
    "tytul",
    "z_rachunku",
)

_MONTHS = {
    "stycznia": 1,
    "lutego": 2,
    "marca": 3,
    "kwietnia": 4,
    "maja": 5,
    "czerwca": 6,
    "lipca": 7,
    "sierpnia": 8,
    "wrzesnia": 9,
    "września": 9,
    "pazdziernika": 10,
    "października": 10,
    "listopada": 11,
    "grudnia": 12,
}

_DATE = re.compile(
    r"(?i)(?:data\s+(?:operacji|realizacji|transakcji|wykonania)|w\s+dniu)"
    r"[\s.:]*"
    r"(\d{4}-\d{2}-\d{2}|\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4}|\d{1,2}\s+[A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+\s+\d{4})"
)
_AMOUNT = re.compile(
    r"(?i)(?:kwota(?:\s+(?:operacji|przelewu))?|kwocie|warto[śs][ćc])"
    r"[\s.:]*(?:PLN|z[łl])?[\s.:]*"
    r"(\d{1,6}(?:[ \u00a0]\d{3})?[,.]\d{2})"
)
_ACCOUNT = re.compile(r"(?i)(?<!\d)(?:PL)?(?:[\s-]*\d){26}(?!\d)")
_TXN = re.compile(r"\b[A-Z]{3}\d{10,16}\b")
_TITLE = re.compile(
    r"(?is)(?:tytu[łl]em|tytu[łl]\s*przelewu|tytu[łl]|opis)\s*[:.]?\s*(.+?)"
    r"(?=\n\s*(?:numer\b|nr\s+ref|identyfikator\s+operacji|status\b|kana[łl]\b|"
    r"typ\s+operacji|op[łl]ata\b|tryb\b|waluta\b|zrealizowano|data\s+\w+|kwota\b|"
    r"warto[śs][ćc]\b|godz\b)|$)"
)
_Z_LABEL = re.compile(
    r"(?i)rachunek\s*(?:obci[aą][żz]any|zleceniodawcy|nadawcy|p[łl]atnika)|z\s*rachunku"
)
_NA_LABEL = re.compile(
    r"(?i)rachunek\s*(?:odbiorcy|beneficjenta|uznawany|adresata)|na\s*rachunek"
)


@dataclass(frozen=True)
class PrzelewExtraction:
    data: dict
    sources: dict[str, str]


def extract_przelew(
    text: str,
    client: LLMClient | None = None,
    *,
    use_llm: bool = True,
) -> PrzelewExtraction:
    values = _from_rules(text or "")
    sources = {field: "rule" for field, value in values.items() if value is not None}
    missing = [field for field in FIELDS if values.get(field) is None]
    if missing and use_llm:
        llm_client = client if client is not None else LLMClient()
        filled = _from_llm(llm_client, text or "", missing)
        for field in missing:
            value = filled.get(field)
            if value is not None:
                values[field] = value
                sources[field] = "llm"
            else:
                sources[field] = "llm"
    payload = {"przelew_bankowy": {field: values.get(field) for field in FIELDS}}
    fallback = "llm" if use_llm else "rule"
    return PrzelewExtraction(
        data=payload,
        sources={field: sources.get(field, fallback) for field in FIELDS},
    )


def _from_rules(text: str) -> dict:
    accounts = _accounts(text)
    z_rachunku = _account_after(text, accounts, _Z_LABEL)
    na_rachunek = _account_after(text, accounts, _NA_LABEL)
    if z_rachunku is None and na_rachunek is None and len(accounts) == 2:
        z_rachunku, na_rachunek = accounts[0][1], accounts[1][1]
    elif z_rachunku is None and na_rachunek is not None:
        others = [digits for _, digits in accounts if digits != na_rachunek]
        if len(others) == 1:
            z_rachunku = others[0]
    elif na_rachunek is None and z_rachunku is not None:
        others = [digits for _, digits in accounts if digits != z_rachunku]
        if len(others) == 1:
            na_rachunek = others[0]
    return {
        "data_operacji": _date(text),
        "kwota": _amount(text),
        "na_rachunek": na_rachunek,
        "numer_transakcji": _transaction(text),
        "tytul": _title(text),
        "z_rachunku": z_rachunku,
    }


def _from_llm(client: LLMClient, text: str, missing: list[str]) -> dict:
    prompt = (
        "Uzupełnij brakujące pola potwierdzenia przelewu. "
        f"Zwróć JSON tylko z kluczami: {', '.join(missing)}. "
        "data_operacji jako YYYY-MM-DD. kwota jako liczba. "
        "na_rachunek i z_rachunku jako same cyfry, bez PL i bez spacji. "
        "numer_transakcji jako identyfikator z tytułu lub treści, albo null. "
        "tytul jako treść tytułu bez cudzysłowów."
    )
    from odwolania.llm_extractor import _przelew_window

    raw = client.extract_json(prompt, _przelew_window(text))
    if isinstance(raw.get("przelew_bankowy"), dict):
        raw = raw["przelew_bankowy"]
    found: dict = {}
    for field in missing:
        if field not in raw:
            continue
        found[field] = _normalize(field, raw[field])
    return found


def _normalize(field: str, value: object) -> object:
    if value is None:
        return None
    if field == "data_operacji":
        return _parse_date(str(value))
    if field == "kwota":
        return _parse_amount(str(value))
    if field in ("na_rachunek", "z_rachunku"):
        digits = re.sub(r"\D", "", str(value))
        return digits if len(digits) == 26 else None
    if field == "numer_transakcji":
        match = _TXN.search(str(value).upper())
        return match.group(0) if match else None
    if field == "tytul":
        return _clean_title(str(value)) or None
    return None


def _date(text: str) -> str | None:
    match = _DATE.search(text)
    if not match:
        return None
    return _parse_date(match.group(1))


def _parse_date(raw: str) -> str | None:
    raw = " ".join(raw.split())
    iso = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if iso:
        return f"{int(iso.group(1)):04d}-{int(iso.group(2)):02d}-{int(iso.group(3)):02d}"
    dotted = re.fullmatch(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})", raw)
    if dotted:
        day, month, year = (int(part) for part in dotted.groups())
        return _ymd(year, month, day)
    written = re.fullmatch(
        r"(\d{1,2})\s+([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+)\s+(\d{4})",
        raw,
    )
    if written:
        month = _MONTHS.get(written.group(2).lower())
        if month is None:
            return None
        return _ymd(int(written.group(3)), month, int(written.group(1)))
    return None


def _ymd(year: int, month: int, day: int) -> str | None:
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _amount(text: str) -> float | None:
    for match in _AMOUNT.finditer(text):
        value = _parse_amount(match.group(1))
        if value is not None and value > 0:
            return value
    return None


def _parse_amount(raw: str) -> float | None:
    cleaned = raw.strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _accounts(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for match in _ACCOUNT.finditer(text):
        digits = re.sub(r"\D", "", match.group(0))
        if len(digits) == 26:
            found.append((match.start(), digits))
    return found


def _account_after(text: str, accounts: list[tuple[int, str]], label: re.Pattern[str]) -> str | None:
    for marker in label.finditer(text):
        for pos, digits in accounts:
            if marker.end() <= pos <= marker.end() + 180:
                return digits
    return None


def _transaction(text: str) -> str | None:
    found = _TXN.findall(text.upper())
    unique = list(dict.fromkeys(found))
    if len(unique) == 1:
        return unique[0]
    return None


def _title(text: str) -> str | None:
    match = _TITLE.search(text)
    if not match:
        return None
    cleaned = _clean_title(match.group(1))
    return cleaned or None


def _clean_title(raw: str) -> str:
    text = " ".join(raw.split())
    while text:
        stripped = text.strip(" \t\"'`„”«»")
        if stripped.endswith("."):
            stripped = stripped[:-1].rstrip()
        if stripped == text:
            break
        text = stripped
    return text

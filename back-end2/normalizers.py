"""Normalize dates, identifiers, amounts, and person names."""

import re

MONTHS = {
    "stycznia": 1,
    "lutego": 2,
    "marca": 3,
    "kwietnia": 4,
    "maja": 5,
    "czerwca": 6,
    "lipca": 7,
    "sierpnia": 8,
    "września": 9,
    "wrzesnia": 9,
    "października": 10,
    "pazdziernika": 10,
    "listopada": 11,
    "grudnia": 12,
}

TITLES = re.compile(
    r"\b(?:r\.\s*pr\.|radca prawny|adwokat|adw\.)\s*",
    re.IGNORECASE,
)


def clean_text(text):
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\xad", "")
    return text


def collapse_spaced_letters(text):
    def join(match):
        return match.group(0).replace(" ", "")

    return re.sub(
        r"(?<!\S)(?:[A-ZĄĆĘŁŃÓŚŹŻ]\s+){3,}[A-ZĄĆĘŁŃÓŚŹŻ](?!\S)",
        join,
        text,
    )


def compact(text):
    return re.sub(r"\s+", " ", clean_text(text)).strip()


def parse_date(value):
    if not value:
        return None
    text = compact(value).lower().rstrip(".")
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return "-".join(match.groups())
    match = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    match = re.search(r"(\d{1,2})\s+([a-ząćęłńóśźż]+)\s+(\d{4})", text)
    if match and match.group(2) in MONTHS:
        return f"{match.group(3)}-{MONTHS[match.group(2)]:02d}-{int(match.group(1)):02d}"
    return None


def digits(value):
    if not value:
        return None
    found = re.sub(r"\D", "", value)
    return found or None


def identifier(value, length=None):
    found = digits(value)
    if not found:
        return None
    if length and len(found) not in length:
        return None
    return found


def account_number(value):
    if not value:
        return None
    match = re.search(r"(?:PL[\s-]*)?((?:\d[\s-]*){26})", value, re.IGNORECASE)
    if not match:
        return None
    found = re.sub(r"\D", "", match.group(1))
    return found if len(found) == 26 else None


def amount(value):
    if value is None:
        return None
    text = compact(str(value)).lower().replace("pln", "").replace("zł", "").replace("zl", "")
    match = re.search(r"(\d[\d\s]*)[.,](\d{2})", text)
    if match:
        whole = match.group(1).replace(" ", "")
        return float(f"{whole}.{match.group(2)}")
    match = re.search(r"(\d[\d\s]*)", text)
    if not match:
        return None
    return float(match.group(1).replace(" ", ""))


def person_name(value):
    if not value:
        return None
    name = TITLES.sub("", value)
    name = name.replace("(", " ").replace(")", " ")
    name = compact(name).strip(" ,.;:-")
    parts = name.split(" ")
    if len(parts) < 2:
        return None
    if not parts[0][:1].isupper():
        return None
    return " ".join(parts[:3])


def bzp_number(value):
    if not value:
        return None
    match = re.search(r"(\d{4})\s*/\s*BZP\s*(\d+)(?:\s*/\s*(\d+))?", value, re.IGNORECASE)
    if not match:
        return None
    number = f"{match.group(1)}/BZP{match.group(2)}"
    if match.group(3):
        number += f"/{match.group(3)}"
    return number


def ted_number(value):
    if not value:
        return None
    match = re.search(r"(\d{4})\s*/\s*S\s*\d{1,3}\s*-\s*(\d{5,7})", value, re.IGNORECASE)
    if match:
        return f"{match.group(2)}-{match.group(1)}"
    match = re.search(r"\b(\d{5,7})\s*-\s*(\d{4})\b", value)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return None


def email(value):
    if not value:
        return None
    match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", value)
    return match.group(0) if match else None


def transaction_id(value):
    if not value:
        return None
    match = re.search(r"\b([A-Z]{2,}[A-Z0-9]*\d{6,})\b", compact(value).upper())
    if match:
        return match.group(1)
    token = compact(value)
    if re.fullmatch(r"[A-Z0-9/-]{6,}", token):
        return token
    return None

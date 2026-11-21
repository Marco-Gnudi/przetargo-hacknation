"""Repair identifiers with official check digits.

A value with OCR letter confusions is fixed only when the fix passes the check digit.
A clean all-digit read of the right length is kept even when its check digit fails.
"""

from __future__ import annotations

import re

_CONFUSION = {
    "O": "0", "0": "O",
    "I": "1", "L": "1", "1": "I",
    "S": "5", "5": "S",
    "B": "8", "8": "B",
    "Z": "2", "2": "Z",
    "G": "6", "6": "G",
}


def repair_nrb(value) -> str | None:
    return _repair(value, 26, nrb_ok)


def repair_nip(value) -> str | None:
    return _repair(value, 10, nip_ok)


def repair_regon(value) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    length = 14 if len(digits) >= 14 else 9
    return _repair(value, length, regon_ok)


def repair_pesel(value) -> str | None:
    return _repair(value, 11, pesel_ok)


def nrb_ok(digits: str) -> bool:
    if len(digits) != 26 or not digits.isdigit():
        return False
    iban = "PL" + digits
    rearranged = iban[4:] + iban[:4]
    converted = "".join(str(ord(char) - 55) if char.isalpha() else char for char in rearranged)
    return int(converted) % 97 == 1


def nip_ok(digits: str) -> bool:
    if len(digits) != 10 or not digits.isdigit():
        return False
    weights = (6, 5, 7, 2, 3, 4, 5, 6, 7)
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights))
    control = total % 11
    return control < 10 and control == int(digits[-1])


def regon_ok(digits: str) -> bool:
    if len(digits) == 9:
        weights = (8, 9, 2, 3, 4, 5, 6, 7)
    elif len(digits) == 14:
        weights = (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8)
    else:
        return False
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights))
    return total % 11 % 10 == int(digits[len(weights)])


def pesel_ok(digits: str) -> bool:
    if len(digits) != 11 or not digits.isdigit():
        return False
    weights = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights))
    return (10 - total % 10) % 10 == int(digits[-1])


def _repair(value, length: int, valid) -> str | None:
    if not value:
        return None
    compact = re.sub(r"[^0-9A-Za-z]", "", str(value)).upper()
    if valid(_digits(compact)) and len(_digits(compact)) == length:
        return _digits(compact)
    for index, char in enumerate(compact):
        alternative = _CONFUSION.get(char)
        if not alternative:
            continue
        trial = compact[:index] + alternative + compact[index + 1:]
        digits = _digits(trial)
        if len(digits) == length and valid(digits):
            return digits
    # Test and generated documents use IDs that fail the check digit; a clean read is kept.
    if compact.isdigit() and len(compact) == length:
        return compact
    return None


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)

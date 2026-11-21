"""Classify a document from its text, not from its filename."""

import re

from pdf_reader import PdfDocument


def classify(document: PdfDocument, rules: dict):
    text = document.text.lower()
    scores = {}
    for name, spec in rules["classes"].items():
        if not _structure(name, text):
            scores[name] = 0
            continue
        score = rules["classification"]["minimum_score"]
        for keyword, weight in spec["keywords"]:
            score += text.count(keyword.lower()) * weight
        if _heading(document.text, spec["heading"]):
            score += 8
        scores[name] = score
    settings = rules["classification"]
    ranking = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_name, best_score = ranking[0]
    second = ranking[1][1] if len(ranking) > 1 else 0
    confident = best_score >= settings["minimum_score"] and best_score >= second + settings["minimum_margin"]
    if not confident:
        return {
            "document_type": "unknown",
            "scores": scores,
            "confident": False,
            "reason": "No class cleared the score margin.",
        }
    return {
        "document_type": best_name,
        "scores": scores,
        "confident": True,
        "reason": f"{best_name} scored {best_score}, next class scored {second}.",
    }


def _structure(name, text):
    if name == "przelew":
        phrases = (
            "polecenie przelewu",
            "potwierdzenie przelewu",
            "potwierdzenie realizacji",
            "potwierdzenie wykonania przelewu",
            "potwierdzenie operacji bankowej",
            "potwierdzenie transakcji",
            "dowód wykonania przelewu",
            "kwota przelewu",
            "rachunek nadawcy",
        )
        has_phrase = any(phrase in text for phrase in phrases)
        has_account = re.search(r"(?:\d[\s-]*){26}", text) is not None
        return has_phrase and has_account
    if name == "odwolanie":
        return _heading(text, "odwołanie", exact=True) and "odwołując" in text and "zamawiając" in text
    if name == "pelnomocnictwo":
        return "pełnomocnictw" in text and (
            "udzielam" in text or "mocodawc" in text or "upoważniam" in text or "ustanawiam" in text
        )
    return False


def _heading(text, phrase, exact=False):
    target = re.sub(r"[^a-ząćęłńóśźż]", "", phrase.lower())
    for line in text.splitlines():
        letters = re.sub(r"[^a-ząćęłńóśźż]", "", line.lower())
        if not letters:
            continue
        if letters == target or (not exact and letters.startswith(target)):
            return True
    return False

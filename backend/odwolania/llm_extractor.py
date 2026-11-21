"""Fill a document JSON from the Bielik prompt stored in document_types.yaml."""

from __future__ import annotations

import hashlib
import os
import json
import re
from dataclasses import dataclass
from pathlib import Path

from odwolania.config import load_settings
from odwolania.llm import LLMClient, MAX_TEXT_CHARS, cache_skipped, load_env

CACHE_DIR = Path(__file__).resolve().parents[1] / ".cache" / "llm"

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

# Gold phrases. Id 6 uses "i", not the slash written in the dictionary file.
_CZYNNOSC_OPIS = {
    1: "Decyzja o odrzuceniu oferty",
    2: "Ogłoszenie wyboru oferty",
    3: "Decyzja o wykluczeniu wykonawcy",
    4: "Publikacja specyfikacji warunków zamówienia (SWZ)",
    5: "Modyfikacja treści SWZ",
    6: "Odpowiedzi i wyjaśnienia do SWZ",
    7: "Zaniechanie odrzucenia oferty",
    8: "Zaniechanie wykluczenia wykonawcy",
    9: "Decyzja o unieważnieniu postępowania",
    10: "Zaniechanie unieważnienia postępowania",
    11: "Opis przedmiotu zamówienia (OPZ)",
    12: "Projektowane postanowienia umowy",
}

_SCHEMAS: dict[str, dict] = {
    "odwolanie": {
        "OdwolanieKIO": {
            "data": "date",
            "czynnosc_dzien": "date",
            "czynnosc_powod_id": "int",
            "czynnosc_opis": "text",
            "miejscowosc": "text",
        },
        "Odwolujacy": [
            {
                "krs": "digits",
                "nazwa": "text",
                "nip": "digits",
                "regon": "digits",
                "przez-pelnomocnika": "bit",
                "pelnomocnik": {
                    "imie_nazwisko": "person",
                    "nazwa": "text",
                    "mail": "text",
                },
            }
        ],
        "Zamawiajacy": [
            {
                "krs": "digits",
                "nazwa": "text",
                "nip": "digits",
                "regon": "digits",
                "prowadzacy_postepowanie": "bit",
            }
        ],
        "ZamowieniePubliczne": {
            "numer_bzp": "bzp",
            "numer_postepowania": "text",
            "numer_ted": "ted",
            "tytul": "text",
        },
    },
    "pelnomocnictwo": {
        "mocodawca": [
            {
                "data": {
                    "imie_nazwisko": "person",
                    "krs": "digits",
                    "nazwa": "text",
                    "nip": "digits",
                    "typ": "typ",
                },
                "podpisujacy": [{"imie_nazwisko": "person"}],
            }
        ],
        "pelnomocnicy": [{"imie_nazwisko": "person", "pesel": "pesel"}],
    },
    "przelew": {
        "przelew_bankowy": {
            "data_operacji": "date",
            "kwota": "amount",
            "na_rachunek": "iban",
            "numer_transakcji": "text",
            "tytul": "text",
            "z_rachunku": "iban",
        }
    },
}

_TITLE = re.compile(
    r"^(?:r\.\s*pr\.|radc(?:a|y|ą)\s+prawn(?:y|a|ego)|adw(?:okat)?\.?|mec\.?)\s+",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LlmExtraction:
    data: dict
    sources: dict[str, str]
    raw: dict | None = None


def extract(
    doc_type: str,
    text: str,
    client: LLMClient | None = None,
    *,
    cache_dir: Path | None = None,
) -> LlmExtraction:
    """Return the schema JSON. Every leaf is sourced from the LLM."""
    if doc_type not in _SCHEMAS:
        raise ValueError(f"No LLM schema for {doc_type}")
    prompt = _prompt(doc_type)
    if _from_ocr():
        prompt += (
            "\n\nTekst pochodzi z OCR i może zawierać błędne znaki. "
            "Popraw oczywiste literówki w nazwach i adresach. "
            "Liczby, daty i numery rachunków przepisz dokładnie tak, jak je widać."
        )
    source = text or ""
    sent = _przelew_window(source) if doc_type == "przelew" else source
    model = _cached_json(prompt, sent, client, cache_dir if cache_dir is not None else CACHE_DIR)
    data = _shape(doc_type, model, normalise=True, text=source)
    raw = _shape(doc_type, model, normalise=False, text=source)
    return LlmExtraction(data=data, sources=_sources(data), raw=raw)


def _prompt(doc_type: str) -> str:
    for item in load_settings().document_types:
        if item.id == doc_type and item.llm_prompt:
            return item.llm_prompt
    raise ValueError(f"No llm_prompt for {doc_type}")


def _env_model() -> str:
    """Model name for the cache key, so replies from different models never mix."""
    load_env()
    return os.environ.get("LLM_MODEL", "")


def _cached_json(prompt: str, text: str, client: LLMClient | None, cache_dir: Path) -> dict:
    clipped = text[:MAX_TEXT_CHARS]
    model_name = getattr(client, "model", "") if client is not None else _env_model()
    digest = hashlib.sha256(f"{model_name}\0{prompt}\0{clipped}".encode("utf-8")).hexdigest()
    path = cache_dir / f"{digest}.json"
    if path.is_file() and not cache_skipped():
        cached = json.loads(path.read_text(encoding="utf-8"))
        return cached if isinstance(cached, dict) else {}
    llm = client if client is not None else LLMClient()
    raw = llm.extract_json(prompt, clipped)
    if raw:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return raw


def _shape(doc_type: str, raw: dict, *, normalise: bool, text: str = "") -> dict:
    payload = raw if isinstance(raw, dict) else {}
    if doc_type == "pelnomocnictwo":
        payload = _nest_signers(payload)
        payload = _lift_attorneys(payload)
    shaped = _apply(_SCHEMAS[doc_type], payload, normalise=normalise)
    if not normalise:
        return shaped
    if doc_type == "odwolanie":
        _finish_odwolanie(shaped, text)
    elif doc_type == "pelnomocnictwo":
        _finish_pelnomocnictwo(shaped)
    elif doc_type == "przelew":
        _finish_przelew(shaped, text)
    if normalise and _from_ocr():
        _reject_bad_ids(shaped)
    return shaped


def normalise_vision(doc_type: str, raw: dict) -> dict:
    """Shape a vision reply and drop identifiers that fail their check digit.

    Unlike the text extractor, a value does not have to occur in the OCR string.
    """
    if doc_type not in _SCHEMAS:
        return {}
    payload = raw if isinstance(raw, dict) else {}
    if doc_type == "pelnomocnictwo":
        payload = _nest_signers(payload)
        payload = _lift_attorneys(payload)
    shaped = _apply(_SCHEMAS[doc_type], payload, normalise=True)
    _reject_bad_ids(shaped)
    return shaped


def _from_ocr() -> bool:
    from odwolania.pdf_reader import OCR_TEXT

    return bool(OCR_TEXT.get())


def _reject_bad_ids(data: dict) -> None:
    """A wrong identifier is a false positive and a false negative. Null is only a miss."""
    import sys

    root = Path(__file__).resolve().parents[2] / "back-end2"
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from checksums import repair_nip, repair_nrb, repair_pesel, repair_regon

    repair = {
        "nip": repair_nip,
        "regon": repair_regon,
        "pesel": repair_pesel,
        "na_rachunek": repair_nrb,
        "z_rachunku": repair_nrb,
    }

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in repair and value:
                    node[key] = repair[key](value)
                elif key == "krs" and value:
                    digits = re.sub(r"\D", "", str(value))
                    node[key] = digits if len(digits) == 10 else None
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)


def _apply(spec: object, raw: object, *, normalise: bool) -> object:
    if isinstance(spec, dict):
        source = raw if isinstance(raw, dict) else {}
        if not source and isinstance(raw, list):
            source = next((item for item in raw if isinstance(item, dict)), {})
        return {key: _apply(child, source.get(key), normalise=normalise) for key, child in spec.items()}
    if isinstance(spec, list):
        items = raw if isinstance(raw, list) else ([raw] if isinstance(raw, dict) else [])
        child = spec[0]
        shaped = []
        for item in items:
            if isinstance(item, str) and isinstance(child, dict) and "imie_nazwisko" in child:
                item = {"imie_nazwisko": item}
            shaped.append(_apply(child, item, normalise=normalise))
        return shaped
    if not normalise:
        return raw if not isinstance(raw, (dict, list)) else None
    return _normalise(str(spec), raw)


def _nest_signers(raw: dict) -> dict:
    """The model sometimes lists signers beside mocodawca instead of inside it."""
    signers = raw.get("podpisujacy")
    principals = raw.get("mocodawca")
    if not isinstance(signers, list) or not isinstance(principals, list) or len(principals) != 1:
        return raw
    principal = principals[0]
    if not isinstance(principal, dict) or principal.get("podpisujacy"):
        return raw
    moved = dict(principal)
    moved["podpisujacy"] = signers
    copied = dict(raw)
    copied["mocodawca"] = [moved]
    return copied


def _finish_odwolanie(data: dict, text: str) -> None:
    kio = data["OdwolanieKIO"]
    powod = kio.get("czynnosc_powod_id")
    if powod not in _CZYNNOSC_OPIS:
        powod = _powod_from_opis(kio.get("czynnosc_opis"))
        kio["czynnosc_powod_id"] = powod
    if powod in _CZYNNOSC_OPIS:
        kio["czynnosc_opis"] = _CZYNNOSC_OPIS[powod]
    # data and miejscowosc come from one header line, never from the act date.
    if kio.get("data") and kio["data"] == kio.get("czynnosc_dzien"):
        kio["data"] = None
        kio["miejscowosc"] = None
    authorities = data["Zamawiajacy"]
    if len(authorities) == 1:
        authorities[0]["prowadzacy_postepowanie"] = None
    order = data["ZamowieniePubliczne"]
    for field in ("numer_postepowania", "numer_bzp"):
        order[field] = _keep_if_present(order.get(field), text)


def _lift_attorneys(raw: dict) -> dict:
    """The model sometimes lists attorneys inside mocodawca instead of beside it."""
    attorneys = raw.get("pelnomocnicy")
    if isinstance(attorneys, list) and attorneys:
        return raw
    lifted: list = []
    principals = raw.get("mocodawca")
    if isinstance(principals, list):
        for principal in principals:
            nested = principal.get("pelnomocnicy") if isinstance(principal, dict) else None
            if isinstance(nested, list):
                lifted.extend(nested)
    if not lifted:
        return raw
    copied = dict(raw)
    copied["pelnomocnicy"] = lifted
    return copied


def _finish_pelnomocnictwo(data: dict) -> None:
    for principal in data["mocodawca"]:
        body = principal["data"]
        kind = body.get("typ")
        if kind not in ("osoba_prawna", "osoba_fizyczna"):
            body["typ"] = "osoba_prawna" if body.get("krs") else (
                "osoba_fizyczna" if body.get("imie_nazwisko") else None
            )


def _powod_from_opis(opis: object) -> int | None:
    text = _fold(opis)
    if not text:
        return None
    text = text.replace("/", " i ")
    for powod, phrase in _CZYNNOSC_OPIS.items():
        if _fold(phrase).replace("/", " i ") == text:
            return powod
    return None


def _sources(value: object, prefix: str = "") -> dict[str, str]:
    found: dict[str, str] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            found.update(_sources(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.update(_sources(item, f"{prefix}[{index}]"))
    elif prefix:
        found[prefix] = "llm"
        found[prefix.rsplit(".", 1)[-1]] = "llm"
    return found


def _normalise(kind: str, value: object) -> object:
    if kind == "date":
        return _date(value)
    if kind == "amount":
        return _amount(value)
    if kind == "iban":
        return _iban(value)
    if kind == "int":
        return _int(value)
    if kind == "bit":
        return _bit(value)
    if kind == "digits":
        return _digits(value)
    if kind == "pesel":
        return _digits(value)
    if kind == "person":
        return _person(value)
    if kind == "bzp":
        return _bzp(value)
    if kind == "ted":
        return _ted(value)
    if kind == "typ":
        return _typ(value)
    return _text(value)


def _text(value: object) -> str | None:
    if value is None or isinstance(value, (dict, list)):
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text or text.casefold() in {"null", "none", "brak", "-", "—"}:
        return None
    return text


def _person(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    # The appeal schema keeps the first attorney when several are named.
    text = text.split(",", 1)[0].strip()
    previous = None
    while text != previous:
        previous = text
        text = _TITLE.sub("", text).strip(" ,")
    return text or None


def _digits(value: object) -> str | None:
    text = _text(value)
    if text is None and isinstance(value, int) and not isinstance(value, bool):
        text = str(value)
    if text is None:
        return None
    digits = re.sub(r"\D", "", text)
    return digits or None


def _int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        number = value
    elif isinstance(value, float):
        number = int(value)
    else:
        text = _text(value)
        if text is None or not re.fullmatch(r"\d{1,2}", text):
            return None
        number = int(text)
    if 1 <= number <= 12:
        return number
    return None


def _bit(value: object) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = int(value)
        return number if number in (0, 1) else None
    text = _text(value)
    if text is None:
        return None
    folded = text.casefold()
    if folded in {"1", "tak", "true", "yes"}:
        return 1
    if folded in {"0", "nie", "false", "no"}:
        return 0
    return None


def _typ(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    folded = text.casefold().replace(" ", "_").replace("-", "_")
    if "fizyczn" in folded:
        return "osoba_fizyczna"
    if "prawn" in folded:
        return "osoba_prawna"
    return None


def _date(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        return _ymd(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    dotted = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", text)
    if dotted:
        return _ymd(int(dotted.group(3)), int(dotted.group(2)), int(dotted.group(1)))
    written = re.search(
        r"(\d{1,2})\s+([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+)\s+(\d{4})",
        text,
    )
    if written:
        month = _MONTHS.get(written.group(2).casefold())
        if month is None:
            return None
        return _ymd(int(written.group(3)), month, int(written.group(1)))
    return None


def _ymd(year: int, month: int, day: int) -> str | None:
    if not (1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _amount(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _text(value)
    if text is None:
        return None
    cleaned = (
        text.replace("\u00a0", "")
        .replace(" ", "")
        .replace("PLN", "")
        .replace("zł", "")
        .replace("zl", "")
    )
    cleaned = cleaned.replace(",", ".")
    if cleaned.count(".") > 1:
        head, _, tail = cleaned.rpartition(".")
        cleaned = head.replace(".", "") + "." + tail
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
        return None
    return float(cleaned)


def _iban(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    digits = re.sub(r"\D", "", re.sub(r"(?i)^PL", "", text.replace(" ", "")))
    return digits or None


def _bzp(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    compact = re.sub(r"\s+", "", text).upper()
    match = re.search(r"\d{4}/BZP\d+(?:/\d{2})?", compact)
    return match.group(0) if match else None


def _ted(value: object) -> str | None:
    text = _text(value)
    if text is None:
        return None
    compact = re.sub(r"\s+", "", text)
    rewritten = re.search(r"(\d{4})/S\d*-(\d{6})", compact, flags=re.IGNORECASE)
    if rewritten:
        return f"{rewritten.group(2)}-{rewritten.group(1)}"
    direct = re.search(r"(\d{6})-(\d{4})", compact)
    if direct:
        return f"{direct.group(1)}-{direct.group(2)}"
    return None


_OPEN_QUOTE = {"„": "”", "“": "”", "«": "»", '"': '"'}
_LOOSE = re.compile(r"[\"„“”«»'\s]+")


def _przelew_window(text: str) -> str:
    """Bank confirmation only, from its header through the Kanał line."""
    start = re.search(
        r"(?i)(?:dotyczy\s*:\s*potwierdzenie|potwierdzenie\s+(?:realizacji|wykonania|przelewu)|bank potwierdza)",
        text,
    )
    tail = text[start.start() :] if start else text
    end = re.search(r"(?i)kana[łl]\s*:", tail)
    if end:
        line_end = tail.find("\n", end.end())
        tail = tail[: line_end if line_end != -1 else end.end()]
    return tail[:2_000]


def _finish_przelew(data: dict, text: str) -> None:
    from odwolania.extractors.przelew import extract_przelew

    body = data["przelew_bankowy"]
    rules = extract_przelew(text, use_llm=False).data["przelew_bankowy"]
    body["tytul"] = _verbatim_title(body.get("tytul"), text, rules.get("tytul"))
    for field in ("na_rachunek", "z_rachunku"):
        body[field] = _ground_digits(body.get(field), text, rules.get(field), width=26)
    body["numer_transakcji"] = _ground_token(body.get("numer_transakcji"), text, rules.get("numer_transakcji"))


def _verbatim_title(model: object, text: str, rule: object) -> str | None:
    """Keep a title only when it occurs in the PDF, and extend it to the full span."""
    model_ok = isinstance(model, str) and bool(model.strip()) and _contains_loose(text, model)
    rule_text = rule.strip() if isinstance(rule, str) else ""
    quoted = _quoted_title(text)
    if model_ok and quoted and _contains_loose(quoted, model):
        return quoted
    if model_ok and rule_text and _contains_loose(rule_text, model):
        return re.sub(r"\s+", " ", rule_text).strip()
    if model_ok:
        return re.sub(r"\s+", " ", model).strip()
    return rule_text or None


def _quoted_title(text: str) -> str | None:
    label = re.search(r"(?is)tytu[łl]\s+przelewu\s*:\s*", text)
    if not label:
        return None
    rest = text[label.end() :]
    opener_at = next((index for index, char in enumerate(rest) if char in _OPEN_QUOTE), None)
    if opener_at is None:
        return None
    closer = _OPEN_QUOTE[rest[opener_at]]
    end = rest.find(closer, opener_at + 1)
    if end == -1:
        return None
    title = re.sub(r"\s+", " ", rest[opener_at + 1 : end]).strip()
    return title or None


def _contains_loose(text: str, value: str) -> bool:
    folded = _LOOSE.sub("", value).casefold()
    return bool(folded) and folded in _LOOSE.sub("", text).casefold()


def _keep_if_present(value: object, text: str) -> object:
    if isinstance(value, str) and _contains_loose(text, value):
        return value
    return None


def _ground_digits(value: object, text: str, rule: object, *, width: int) -> str | None:
    digits_in_text = re.sub(r"\D", "", text)
    if isinstance(value, str) and len(value) == width and value in digits_in_text:
        return value
    if isinstance(rule, str) and len(rule) == width and rule in digits_in_text:
        return rule
    return None


def _ground_token(value: object, text: str, rule: object) -> str | None:
    if isinstance(value, str) and value and re.search(re.escape(value), text, flags=re.IGNORECASE):
        return value
    if isinstance(rule, str) and rule and re.search(re.escape(rule), text, flags=re.IGNORECASE):
        return rule
    return None


def _fold(value: object) -> str:
    text = _text(value) or ""
    return re.sub(r"\s+", " ", text).casefold()

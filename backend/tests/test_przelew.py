from odwolania.extractors.przelew import extract_przelew


_COMPLETE = """
POLECENIE PRZELEWU
Potwierdzenie realizacji polecenia przelewu
Rachunek obciążany
PL05470680287581539721455024
Rachunek odbiorcy
PL68438223049992295262834736
Kwota operacji
200,00 PLN
Data transakcji
2026-03-21
Opis
opłata skarbowa od pełnomocnictwa CEN2604016344389
Nr ref.
CEN2604016344389
"""


class _Boom:
    def extract_json(self, prompt: str, text: str) -> dict:
        raise AssertionError("LLM should not be called")


class _Fake:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def extract_json(self, prompt: str, text: str) -> dict:
        self.prompts.append(prompt)
        return {"numer_transakcji": "id CEN2601015794125 w tytule"}


def test_rules_fill_every_field_without_llm():
    extracted = extract_przelew(_COMPLETE, client=_Boom())
    body = extracted.data["przelew_bankowy"]
    assert body["data_operacji"] == "2026-03-21"
    assert body["kwota"] == 200.0
    assert body["z_rachunku"] == "05470680287581539721455024"
    assert body["na_rachunek"] == "68438223049992295262834736"
    assert body["numer_transakcji"] == "CEN2604016344389"
    assert body["tytul"] == "opłata skarbowa od pełnomocnictwa CEN2604016344389"
    assert set(extracted.sources.values()) == {"rule"}


def test_spaced_account_polish_date_and_dotted_amount():
    text = """
    Potwierdzenie przelewu krajowego
    Z rachunku
    09 5706 3749 5036 1862 8466 4881
    Na rachunek
    PL68 4382 2304 9992 2952 6283 4736
    KWOTA PRZELEWU ....................................... 50,00 PLN
    DATA REALIZACJI ..................................... 23 sierpnia 2026
    TYTUŁ:
    „opłata skarbowa”.
    NUMER REFERENCYJNY ............................ CEN2603024646444
    """
    body = extract_przelew(text, client=_Boom()).data["przelew_bankowy"]
    assert body["z_rachunku"] == "09570637495036186284664881"
    assert body["na_rachunek"] == "68438223049992295262834736"
    assert body["kwota"] == 50.0
    assert body["data_operacji"] == "2026-08-23"
    assert body["tytul"] == "opłata skarbowa"
    assert body["numer_transakcji"] == "CEN2603024646444"


def test_missing_transaction_id_goes_to_llm_only():
    text = _COMPLETE.replace("CEN2604016344389", "BRAK")
    fake = _Fake()
    extracted = extract_przelew(text, client=fake)
    body = extracted.data["przelew_bankowy"]
    assert body["numer_transakcji"] == "CEN2601015794125"
    assert extracted.sources["numer_transakcji"] == "llm"
    assert extracted.sources["kwota"] == "rule"
    assert extracted.sources["tytul"] == "rule"
    assert len(fake.prompts) == 1
    assert "kluczami: numer_transakcji." in fake.prompts[0]

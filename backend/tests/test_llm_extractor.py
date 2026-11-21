from odwolania.config import task_data_dir
from odwolania.llm_extractor import LlmExtraction, extract
from odwolania.pipeline import process_document, process_file

_CASE = task_data_dir() / "dane" / "przyklad_01"


class _Fake:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls = 0
        self.prompts: list[str] = []

    def extract_json(self, prompt: str, text: str) -> dict:
        self.calls += 1
        self.prompts.append(prompt)
        return self.payload


def test_odwolanie_shape_normalises_and_caches(tmp_path):
    payload = {
        "OdwolanieKIO": {
            "miejscowosc": " Gdańsk ",
            "czynnosc_opis": "Odpowiedzi/wyjaśnienia do SWZ",
            "czynnosc_powod_id": "6",
            "czynnosc_dzien": "22 sierpnia 2026",
            "data": "3 września 2026 roku",
        },
        "Odwolujacy": {
            "nazwa": "Hartica Serwis S.A.",
            "krs": "999-966-9444",
            "przez-pelnomocnika": "tak",
            "pelnomocnik": {
                "imie_nazwisko": "adw. Bartosz Szymanski",
                "mail": " biuro@kontakt.example ",
            },
        },
        "Zamawiajacy": [
            {"nazwa": "Eurosept Infrastruktura S.A.", "prowadzacy_postepowanie": 1}
        ],
        "ZamowieniePubliczne": {
            "numer_ted": "2026/S086-999073",
            "numer_bzp": "2026/BZP 00999778",
            "tytul": " Dostawa materiałów ",
        },
    }
    client = _Fake(payload)
    first = extract("odwolanie", "tekst odwołania", client, cache_dir=tmp_path)
    second = extract("odwolanie", "tekst odwołania", client, cache_dir=tmp_path)

    assert client.calls == 1
    assert "6=Odpowiedzi/wyjaśnienia do SWZ" in client.prompts[0]
    assert list(first.data) == [
        "OdwolanieKIO",
        "Odwolujacy",
        "Zamawiajacy",
        "ZamowieniePubliczne",
    ]
    assert list(first.data["OdwolanieKIO"]) == [
        "data",
        "czynnosc_dzien",
        "czynnosc_powod_id",
        "czynnosc_opis",
        "miejscowosc",
    ]
    kio = first.data["OdwolanieKIO"]
    assert kio["data"] == "2026-09-03"
    assert kio["czynnosc_dzien"] == "2026-08-22"
    assert kio["czynnosc_powod_id"] == 6
    assert kio["czynnosc_opis"] == "Odpowiedzi i wyjaśnienia do SWZ"
    appellant = first.data["Odwolujacy"][0]
    assert appellant["krs"] == "9999669444"
    assert appellant["nip"] is None
    assert appellant["pelnomocnik"]["imie_nazwisko"] == "Bartosz Szymanski"
    assert appellant["pelnomocnik"]["nazwa"] is None
    assert first.data["Zamawiajacy"][0]["prowadzacy_postepowanie"] is None
    order = first.data["ZamowieniePubliczne"]
    assert order["numer_bzp"] == "2026/BZP00999778"
    assert order["numer_postepowania"] is None
    assert order["numer_ted"] == "999073-2026"
    assert first.sources["OdwolanieKIO.data"] == "llm"
    assert second.data == first.data


def test_first_attorney_is_kept_when_several_are_listed(tmp_path):
    client = _Fake(
        {
            "Odwolujacy": [
                {"pelnomocnik": {"imie_nazwisko": "Halina Walczak, r. pr. Bartosz Bartoszewicz"}}
            ]
        }
    )
    extracted = extract("odwolanie", "odwołanie", client, cache_dir=tmp_path)
    assert extracted.data["Odwolujacy"][0]["pelnomocnik"]["imie_nazwisko"] == "Halina Walczak"


def test_przelew_prompt_normalises_iban_and_amount(tmp_path):
    client = _Fake(
        {
            "przelew_bankowy": {
                "kwota": "1 234,50 PLN",
                "na_rachunek": "PL60 1010 1010 0081 3622 3100 0000",
                "data_operacji": "09.10.2025",
            }
        }
    )
    extracted = extract("przelew", "potwierdzenie", client, cache_dir=tmp_path)
    transfer = extracted.data["przelew_bankowy"]
    assert list(transfer) == [
        "data_operacji",
        "kwota",
        "na_rachunek",
        "numer_transakcji",
        "tytul",
        "z_rachunku",
    ]
    assert transfer["data_operacji"] == "2025-10-09"
    assert transfer["kwota"] == 1234.5
    assert transfer["na_rachunek"] == "60101010100081362231000000"
    assert transfer["numer_transakcji"] is None
    assert set(extracted.sources.values()) == {"llm"}


def test_header_date_copied_from_the_act_is_cleared(tmp_path):
    client = _Fake(
        {
            "OdwolanieKIO": {
                "data": "2026-03-20",
                "czynnosc_dzien": "2026-03-20",
                "czynnosc_powod_id": 9,
                "miejscowosc": "Łódź",
            }
        }
    )
    extracted = extract("odwolanie", "odwołanie", client, cache_dir=tmp_path)
    assert extracted.data["OdwolanieKIO"]["data"] is None
    assert extracted.data["OdwolanieKIO"]["miejscowosc"] is None
    assert extracted.data["OdwolanieKIO"]["czynnosc_dzien"] == "2026-03-20"


def test_signers_placed_beside_the_principal_are_nested(tmp_path):
    client = _Fake(
        {
            "mocodawca": [{"data": {"nazwa": "Belmoria Rozwiązania S.A.", "krs": "9999405188"}}],
            "podpisujacy": [{"imie_nazwisko": "Oliwia Kaczmarek"}],
            "pelnomocnicy": [{"imie_nazwisko": "Aleksandra Marciniak"}],
        }
    )
    extracted = extract("pelnomocnictwo", "pełnomocnictwo", client, cache_dir=tmp_path)
    assert extracted.data["mocodawca"][0]["podpisujacy"] == [
        {"imie_nazwisko": "Oliwia Kaczmarek"}
    ]


def test_attorneys_nested_in_the_principal_are_lifted(tmp_path):
    client = _Fake(
        {
            "mocodawca": [
                {
                    "data": {"nazwa": "Umbria Rozwiązania sp. j.", "krs": "9997927279"},
                    "pelnomocnicy": [
                        {"imie_nazwisko": "Bartosz Jastrzębski"},
                        {"imie_nazwisko": "Oliwia Zajkowski"},
                    ],
                }
            ]
        }
    )
    extracted = extract("pelnomocnictwo", "pełnomocnictwo", client, cache_dir=tmp_path)
    assert [item["imie_nazwisko"] for item in extracted.data["pelnomocnicy"]] == [
        "Bartosz Jastrzębski",
        "Oliwia Zajkowski",
    ]


def test_regular_mode_does_not_call_the_llm_extractor(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("LLM extractor should not run in regular mode")

    monkeypatch.setattr("odwolania.pipeline.extract_llm", boom)
    processed = process_file(_CASE / "odwolanie.pdf", mode="regular")
    assert processed.document_type == "odwolanie"
    assert processed.data == {}
    assert processed.sources == {}


def test_bielik_mode_and_cli_use_the_llm_extractor(monkeypatch):
    def fake(doc_type, text, client=None, **kwargs):
        assert doc_type == "pelnomocnictwo"
        assert "PEŁNOMOCNICTWO" in text
        return LlmExtraction(
            {"mocodawca": [], "pelnomocnicy": []},
            {"mocodawca": "llm"},
        )

    monkeypatch.setattr("odwolania.pipeline.extract_llm", fake)
    processed = process_file(_CASE / "pelnomocnictwo.pdf", mode="bielik")
    assert processed.document_type == "pelnomocnictwo"
    assert processed.data == {"mocodawca": [], "pelnomocnicy": []}
    assert process_document(_CASE / "pelnomocnictwo.pdf") == processed.data

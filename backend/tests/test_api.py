from pathlib import Path

from fastapi.testclient import TestClient

from odwolania.api import app
from odwolania.classifier import classify_with_llm
from odwolania.config import task_data_dir
from odwolania.extractors.przelew import extract_przelew
from odwolania.pipeline import process_file

_CASE = task_data_dir() / "dane" / "przyklad_01"


class _BoomClient:
    def extract_json(self, prompt: str, text: str) -> dict:
        raise AssertionError("LLM should not be called")


class _BoomCtor:
    def __init__(self, *args, **kwargs):
        raise AssertionError("LLM should not be constructed")


def test_regular_extraction_skips_the_llm_when_a_field_is_missing():
    text = "Potwierdzenie przelewu\nKwota 10,00 PLN\n"
    extracted = extract_przelew(text, client=_BoomClient(), use_llm=False)
    assert extracted.data["przelew_bankowy"]["kwota"] == 10.0
    assert extracted.sources["kwota"] == "rule"
    assert extracted.sources["numer_transakcji"] == "rule"
    assert extracted.data["przelew_bankowy"]["numer_transakcji"] is None


def test_llm_classifier_accepts_only_configured_types():
    class _Fake:
        def extract_json(self, prompt: str, text: str) -> dict:
            return {"type": "faktura"}

    assert classify_with_llm("tekst", client=_Fake()) is None


def test_process_przyklad_01_regular_does_not_construct_a_client(monkeypatch):
    monkeypatch.setattr("odwolania.llm.LLMClient", _BoomCtor)
    monkeypatch.setattr("odwolania.extractors.przelew.LLMClient", _BoomCtor)
    monkeypatch.setattr("odwolania.pipeline.classify_with_llm", _BoomCtor)
    pdf = _CASE / "potwierdzenie_przelewu.pdf"
    processed = process_file(pdf, mode="regular")
    assert processed.document_type == "przelew"
    assert processed.data["przelew_bankowy"]["kwota"] == 200.0
    assert set(processed.sources.values()) == {"rule"}


def test_health_and_process_przyklad_01():
    client = TestClient(app)
    assert client.get("/api/health").json() == {"status": "ok"}
    uploads = []
    handles = []
    for name in ("odwolanie.pdf", "pelnomocnictwo.pdf", "potwierdzenie_przelewu.pdf"):
        handle = (_CASE / name).open("rb")
        handles.append(handle)
        uploads.append(("files", (name, handle, "application/pdf")))
    try:
        response = client.post("/api/process", data={"mode": "regular"}, files=uploads)
    finally:
        for handle in handles:
            handle.close()
    assert response.status_code == 200
    body = response.json()
    assert [item["type"] for item in body["files"]] == [
        "odwolanie",
        "pelnomocnictwo",
        "przelew",
    ]
    transfer = body["files"][2]
    assert transfer["json"]["przelew_bankowy"]["numer_transakcji"] == "CEN2604016344389"
    assert transfer["sources"]["na_rachunek"] == "rule"

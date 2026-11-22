import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pymupdf as fitz
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "back-end2"))

import engine  # noqa: E402
from odwolania import llm  # noqa: E402

SAMPLE = ROOT / "UZP-hacknation-task" / "dane" / "przyklad_01"
KEY_VARS = ("LLM_API_KEY", "MISTRAL_API_KEY", "LLM_BASE_URL", "MISTRAL_BASE_URL", "LLM_MODEL", "MISTRAL_MODEL")


def _load_main():
    spec = importlib.util.spec_from_file_location("przetargo_main", ROOT / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def no_key(monkeypatch):
    for name in KEY_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(llm, "load_env", lambda: None)


@pytest.mark.parametrize(
    ("name", "mode"),
    [("deterministic", "regular"), ("hybrid", "bielik"), ("Mistral", "bielik"), ("llm-only", "bielik_only"), ("regular", "regular")],
)
def test_mode_names_map_to_engine_modes(name, mode):
    assert engine.normalise_mode(name) == mode


def test_unknown_mode_is_refused():
    with pytest.raises(ValueError):
        engine.normalise_mode("gpt")


def test_scaleway_mistral_small_is_the_default(no_key):
    assert llm.llm_setting("LLM_BASE_URL") == "https://api.scaleway.ai/v1"
    assert llm.llm_setting("LLM_MODEL") == "mistral-small-3.2-24b-instruct-2506"
    assert llm.llm_setting("LLM_API_KEY") == ""
    assert not llm.server_key_configured()


def test_mistral_variables_are_read_and_llm_variables_win(no_key, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "from-mistral")
    monkeypatch.setenv("MISTRAL_MODEL", "mistral-small-2603")
    assert llm.llm_setting("LLM_API_KEY") == "from-mistral"
    assert llm.llm_setting("LLM_MODEL") == "mistral-small-2603"
    assert llm.server_key_configured()
    monkeypatch.setenv("LLM_API_KEY", "from-llm")
    assert llm.llm_setting("LLM_API_KEY") == "from-llm"


def _make_input(tmp_path: Path) -> Path:
    case = tmp_path / "input" / "nested" / "case1"
    case.mkdir(parents=True)
    for pdf in SAMPLE.glob("*.pdf"):
        shutil.copy(pdf, case / pdf.name)
    shutil.copy(SAMPLE / "potwierdzenie_przelewu.pdf", case / "scan_0001.pdf")
    other = fitz.open()
    other.new_page().insert_text((72, 72), "Menu restauracji: zupa pomidorowa, pierogi, kompot.")
    other.save(case / "menu.pdf")
    return tmp_path / "input"


def test_batch_writes_one_json_per_pdf_and_classifies_by_content(tmp_path, no_key):
    source = _make_input(tmp_path)
    output = tmp_path / "output"
    code = _load_main().main(["--input", str(source), "--output", str(output), "--workers", "2"])
    assert code == 0
    folder = output / "nested" / "case1"
    assert {path.name for path in folder.glob("*.json")} == {
        "odwolanie.json",
        "pelnomocnictwo.json",
        "potwierdzenie_przelewu.json",
        "scan_0001.json",
        "menu.json",
    }
    assert "przelew_bankowy" in json.loads((folder / "scan_0001.json").read_text(encoding="utf-8"))
    assert json.loads((folder / "menu.json").read_text(encoding="utf-8")) == {}
    expected = json.loads((ROOT / "UZP-hacknation-task" / "oczekiwane-json" / "przelew.json").read_text(encoding="utf-8"))
    assert json.loads((folder / "potwierdzenie_przelewu.json").read_text(encoding="utf-8")).keys() == expected.keys()
    log = [json.loads(line) for line in (output / "_logs" / "processing.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(log) == 5 and all(record["llm"]["calls"] == 0 for record in log)


def test_hybrid_without_a_key_stops_before_processing(tmp_path, no_key):
    source = _make_input(tmp_path)
    output = tmp_path / "output"
    assert _load_main().main(["--input", str(source), "--output", str(output), "--mode", "hybrid"]) == 2
    assert not list(output.rglob("*.json"))

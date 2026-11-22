import shutil
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "back-end2"))

import api  # noqa: E402

PRZELEW = ROOT / "UZP-hacknation-task" / "dane" / "przyklad_01" / "potwierdzenie_przelewu.pdf"


def _client(tmp_path, monkeypatch):
    monkeypatch.delenv("PRZETARGO_HOSTED", raising=False)
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "INPUT_ROOT", tmp_path / "input")
    monkeypatch.setattr(api, "OUTPUT_ROOT", tmp_path / "output")
    return TestClient(api.app)


def test_lists_150_pdfs_and_loose_files(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    case = tmp_path / "input" / "case1"
    case.mkdir(parents=True)
    for index in range(150):
        shutil.copy(PRZELEW, case / f"przelew_{index:03}.pdf")
    shutil.copy(PRZELEW, tmp_path / "input" / "luzem.pdf")

    cases = {item["name"]: item["files"] for item in client.get("/api/input").json()["cases"]}

    assert len(cases["case1"]) == 150
    assert [file["name"] for file in cases[api.ROOT_CASE]] == ["luzem.pdf"]


def test_one_file_request_writes_its_json(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    case = tmp_path / "input" / "case7"
    case.mkdir(parents=True)
    shutil.copy(PRZELEW, case / "przelew.pdf")
    shutil.copy(PRZELEW, tmp_path / "input" / "luzem.pdf")

    body = client.post("/api/extract/input/file", json={"case": "case7", "file": "przelew.pdf"}).json()
    loose = client.post("/api/extract/input/file", json={"case": api.ROOT_CASE, "file": "luzem.pdf"}).json()

    assert body["result"]["document_type"] == "przelew"
    assert body["result"]["output"] == "output/case7/przelew.json"
    assert (tmp_path / "output" / "case7" / "przelew.json").is_file()
    assert loose["result"]["output"] == "output/luzem.json"
    assert "elapsed_seconds" in body and "usage" in body


def test_one_file_request_stays_inside_input(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    (tmp_path / "input" / "case1").mkdir(parents=True)
    for case, file in (("..", "x.pdf"), ("case1", "../x.pdf"), ("case1", "missing.pdf")):
        response = client.post("/api/extract/input/file", json={"case": case, "file": file})
        assert response.status_code == 404

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "back-end2"))

import api  # noqa: E402

PRZELEW = ROOT / "UZP-hacknation-task" / "dane" / "przyklad_01" / "potwierdzenie_przelewu.pdf"


def test_batches_join_one_case_and_keep_files_with_the_same_name(tmp_path, monkeypatch):
    monkeypatch.delenv("PRZETARGO_HOSTED", raising=False)
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "INPUT_ROOT", tmp_path / "input")
    monkeypatch.setattr(api, "OUTPUT_ROOT", tmp_path / "output")
    client = TestClient(api.app)
    data = PRZELEW.read_bytes()

    first = client.post("/api/extract/batch", data={"mode": "regular"}, files=[("files", ("przelew.pdf", data, "application/pdf"))])
    case = first.json()["case"]
    second = client.post(
        "/api/extract/batch",
        data={"mode": "regular", "case": case},
        files=[("files", ("przelew.pdf", data, "application/pdf"))],
    )

    assert second.json()["case"] == case == "case1"
    assert sorted(path.name for path in (tmp_path / "output" / case).iterdir()) == ["przelew.json", "przelew_2.json"]
    assert second.json()["results"][0]["status"] == "ok"


def test_a_case_name_outside_the_pattern_starts_a_new_case(tmp_path, monkeypatch):
    monkeypatch.delenv("PRZETARGO_HOSTED", raising=False)
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "INPUT_ROOT", tmp_path / "input")
    monkeypatch.setattr(api, "OUTPUT_ROOT", tmp_path / "output")
    response = TestClient(api.app).post(
        "/api/extract/batch",
        data={"mode": "regular", "case": "../etc"},
        files=[("files", ("przelew.pdf", PRZELEW.read_bytes(), "application/pdf"))],
    )
    assert response.json()["case"] == "case1"
    assert not (tmp_path / "etc").exists()

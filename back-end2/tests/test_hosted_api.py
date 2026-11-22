import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

import api

SAMPLE = api.DATASET / "przyklad_01" / "potwierdzenie_przelewu.pdf"


class HostedApiTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"PRZETARGO_HOSTED": "1", "LLM_API_KEY": ""})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(api.app)

    def test_health_reports_hosted_without_a_server_key(self):
        body = self.client.get("/api/health").json()
        self.assertTrue(body["hosted"])
        self.assertFalse(body["server_key"])

    def test_input_folder_is_closed(self):
        self.assertEqual(self.client.get("/api/input").json(), {"cases": []})
        self.assertEqual(self.client.delete("/api/input").status_code, 404)
        response = self.client.post("/api/extract/input", json={"cases": ["case1"]})
        self.assertEqual(response.status_code, 404)

    def test_bielik_mode_without_a_key_is_refused(self):
        with SAMPLE.open("rb") as handle:
            response = self.client.post(
                "/api/extract/batch",
                data={"mode": "bielik"},
                files={"files": (SAMPLE.name, handle, "application/pdf")},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "llm_key_missing")

    def test_regular_batch_writes_nothing_to_disk(self):
        before = set(api.INPUT_ROOT.iterdir()) if api.INPUT_ROOT.is_dir() else set()
        with SAMPLE.open("rb") as handle:
            response = self.client.post(
                "/api/extract/batch",
                data={"mode": "regular"},
                files={"files": (SAMPLE.name, handle, "application/pdf")},
            )
        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(body["case"])
        self.assertEqual(body["results"][0]["document_type"], "przelew")
        self.assertNotIn("output", body["results"][0])
        after = set(api.INPUT_ROOT.iterdir()) if api.INPUT_ROOT.is_dir() else set()
        self.assertEqual(before, after)

    def test_plain_http_base_url_is_refused(self):
        response = self.client.post(
            "/api/llm/check",
            headers={"X-LLM-Key": "k", "X-LLM-Base-Url": "http://169.254.169.254/"},
        )
        self.assertEqual(response.status_code, 400)

    def test_samples_list_text_and_scan_cases_and_serve_their_files(self):
        samples = self.client.get("/api/samples").json()["samples"]
        kinds = {sample["kind"] for sample in samples}
        self.assertEqual(kinds, {"text", "scan"})
        first = samples[0]["files"][0]
        response = self.client.get("/api/samples/file", params={"path": first["path"]})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_sample_file_stays_inside_the_dataset(self):
        for path in ("../../back-end2/api.py", "../README.md", "przyklad_01/przelew.json"):
            response = self.client.get("/api/samples/file", params={"path": path})
            self.assertEqual(response.status_code, 404, path)


if __name__ == "__main__":
    unittest.main()

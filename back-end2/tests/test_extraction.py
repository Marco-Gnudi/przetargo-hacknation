import json
import unittest
from pathlib import Path

from benchmark import score_pair
from normalizers import account_number, amount, bzp_number, parse_date, person_name, ted_number
from pipeline import process_pdf

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "UZP-hacknation-task" / "dane"


class NormalizerTests(unittest.TestCase):
    def test_dates_amounts_and_ids(self):
        self.assertEqual(parse_date("20 marca 2026"), "2026-03-20")
        self.assertEqual(parse_date("02.07.2026"), "2026-07-02")
        self.assertEqual(amount("PLN 200.00"), 200.0)
        self.assertEqual(amount("15 000,00 zł"), 15000.0)
        self.assertEqual(account_number("PL05 4706 8028 7581 5397 2145 5024"), "05470680287581539721455024")
        self.assertEqual(bzp_number("2026/BZP 00999263"), "2026/BZP00999263")
        self.assertEqual(ted_number("numer ogłoszenia TED: 999137-2026"), "999137-2026")
        self.assertEqual(person_name("adw. Aleksandra Wierzbicka"), "Aleksandra Wierzbicka")
        self.assertEqual(person_name("r. pr. Cezary Bartoszewicz nr wpisu"), "Cezary Bartoszewicz")
        self.assertIsNone(person_name("adw."))


class CaseTests(unittest.TestCase):
    def test_przyklad_01_matches_reference(self):
        folder = DATA / "przyklad_01"
        expected = {
            "odwolanie.pdf": "odwolanie.json",
            "pelnomocnictwo.pdf": "pelnomocnictwo.json",
            "potwierdzenie_przelewu.pdf": "przelew.json",
        }
        for pdf_name, json_name in expected.items():
            payload, diagnostic = process_pdf(folder / pdf_name)
            gold = json.loads((folder / json_name).read_text(encoding="utf-8"))
            counts, fields = score_pair(payload, gold)
            missed = [item for item in fields if item[1] != "tp"]
            self.assertFalse(missed, f"{pdf_name} {diagnostic['document_type']} {missed}")

    def test_reported_extraction_errors(self):
        checks = {
            ("przyklad_11", "pelnomocnictwo.pdf", "pelnomocnictwo.json"): [
                "mocodawca[0].data.nazwa",
                "pelnomocnicy[0].imie_nazwisko",
            ],
            ("przyklad_15", "pelnomocnictwo.pdf", "pelnomocnictwo.json"): [
                "mocodawca[0].podpisujacy[0].imie_nazwisko",
            ],
            ("przyklad_20", "odwolanie.pdf", "odwolanie.json"): [
                "Odwolujacy[0].pelnomocnik.imie_nazwisko",
            ],
            ("przyklad_20", "pelnomocnictwo.pdf", "pelnomocnictwo.json"): [
                "pelnomocnicy[0].imie_nazwisko",
                "pelnomocnicy[1].imie_nazwisko",
            ],
            ("przyklad_33", "pelnomocnictwo.pdf", "pelnomocnictwo.json"): [
                "mocodawca[0].podpisujacy[0].imie_nazwisko",
            ],
            ("przyklad_33", "potwierdzenie_przelewu.pdf", "przelew.json"): [
                "przelew_bankowy.kwota",
                "przelew_bankowy.tytul",
                "przelew_bankowy.data_operacji",
            ],
            ("przyklad_58", "odwolanie.pdf", "odwolanie.json"): [
                "Odwolujacy[0].krs",
                "Zamawiajacy[0].nazwa",
                "Zamawiajacy[0].krs",
                "Zamawiajacy[0].nip",
            ],
        }
        for (folder, pdf_name, json_name), paths in checks.items():
            payload, _ = process_pdf(DATA / folder / pdf_name)
            gold = json.loads((DATA / folder / json_name).read_text(encoding="utf-8"))
            _, fields = score_pair(payload, gold)
            missed = [item for item in fields if item[0] in paths and item[1] != "tp"]
            self.assertFalse(missed, missed)

    def test_przyklad_39_stays_correct(self):
        folder = DATA / "przyklad_39"
        expected = {
            "odwolanie.pdf": "odwolanie.json",
            "pelnomocnictwo.pdf": "pelnomocnictwo.json",
            "potwierdzenie_przelewu.pdf": "przelew.json",
        }
        for pdf_name, json_name in expected.items():
            payload, _ = process_pdf(folder / pdf_name)
            gold = json.loads((folder / json_name).read_text(encoding="utf-8"))
            _, fields = score_pair(payload, gold)
            missed = [item for item in fields if item[1] != "tp"]
            self.assertFalse(missed, missed)

    def test_negative_notice_is_empty(self):
        payload, diagnostic = process_pdf(DATA / "negatywne" / "Broszura_JPK_FA(2).pdf")
        self.assertEqual(payload, {})
        self.assertEqual(diagnostic["document_type"], "unknown")


if __name__ == "__main__":
    unittest.main()

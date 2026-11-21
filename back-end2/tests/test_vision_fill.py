"""Vision is allowed to fill a hole. It is not allowed to replace a valid value."""

import unittest

from vision_fill import merge_vision, needs_vision


class NeedsVisionTests(unittest.TestCase):
    def test_text_pdf_is_left_alone(self):
        payload = {"przelew_bankowy": {"kwota": None}}
        self.assertFalse(needs_vision("przelew", payload, text_source="text", confidence=10))

    def test_null_required_field_on_a_scan(self):
        payload = {"przelew_bankowy": {
            "data_operacji": "2026-01-01",
            "kwota": 17.0,
            "na_rachunek": "60101010100081362231000000",
            "z_rachunku": "68109015051005244171243731",
            "tytul": "wpis",
            "numer_transakcji": None,
        }}
        self.assertTrue(needs_vision("przelew", payload, text_source="ocr", confidence=90))

    def test_low_confidence_even_when_fields_are_full(self):
        payload = {"przelew_bankowy": {
            "data_operacji": "2026-01-01",
            "kwota": 17.0,
            "na_rachunek": "60101010100081362231000000",
            "z_rachunku": "68109015051005244171243731",
            "tytul": "wpis",
            "numer_transakcji": "ABC123",
        }}
        self.assertTrue(needs_vision("przelew", payload, text_source="ocr", confidence=40))
        self.assertFalse(needs_vision("przelew", payload, text_source="ocr", confidence=90))


class MergeVisionTests(unittest.TestCase):
    def test_fills_a_null_and_keeps_a_valid_account(self):
        base = {"przelew_bankowy": {
            "tytul": "wpis od odwołania",
            "na_rachunek": "60101010100081362231000000",
            "numer_transakcji": None,
        }}
        incoming = {"przelew_bankowy": {
            "tytul": "inny tytuł",
            "na_rachunek": "00000000000000000000000000",
            "numer_transakcji": "305494",
        }}
        merged = merge_vision(base, incoming)
        self.assertEqual(merged["przelew_bankowy"]["tytul"], "wpis od odwołania")
        self.assertEqual(merged["przelew_bankowy"]["na_rachunek"], "60101010100081362231000000")
        self.assertEqual(merged["przelew_bankowy"]["numer_transakcji"], "305494")

    def test_replaces_an_identifier_that_fails_its_check(self):
        base = {"Odwolujacy": [{"nip": "1234567890"}]}
        incoming = {"Odwolujacy": [{"nip": "9992956550"}]}
        merged = merge_vision(base, incoming)
        self.assertEqual(merged["Odwolujacy"][0]["nip"], "9992956550")

    def test_appends_a_party_the_rules_missed(self):
        base = {"mocodawca": [{"data": {"nazwa": "Lider"}}]}
        incoming = {"mocodawca": [
            {"data": {"nazwa": "Lider inny"}},
            {"data": {"nazwa": "Lumidor Budownictwo"}},
        ]}
        merged = merge_vision(base, incoming)
        self.assertEqual(len(merged["mocodawca"]), 2)
        self.assertEqual(merged["mocodawca"][0]["data"]["nazwa"], "Lider")
        self.assertEqual(merged["mocodawca"][1]["data"]["nazwa"], "Lumidor Budownictwo")


if __name__ == "__main__":
    unittest.main()

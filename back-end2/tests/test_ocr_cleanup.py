"""OCR text is cleaned before extraction."""

import unittest

from checksums import nip_ok, nrb_ok, repair_nrb
from normalizers import parse_date, ted_number
from ocr_cleanup import cleanup_ocr


class OcrCleanupTests(unittest.TestCase):
    def test_lookalikes_change_only_inside_a_digit_run(self):
        cleaned = cleanup_ocr("rachunek 12O45l S5B8, Sąd KIO Bank")
        self.assertIn("1204515588", cleaned)
        self.assertIn("Sąd KIO Bank", cleaned)

    def test_broken_iban_and_nip_are_joined(self):
        cleaned = cleanup_ocr(
            "NIP 525-000-81-92\nPL60 1010 1010 0081 3622 3100 0000"
        )
        self.assertIn("5250008192", cleaned)
        self.assertIn("PL60101010100081362231000000", cleaned)

    def test_quotes_and_whitespace_are_normalised(self):
        cleaned = cleanup_ocr("„opłata   skarbowa”\r\n\r\n\r\nkoniec")
        self.assertEqual(cleaned, '"opłata skarbowa"\n\nkoniec')

    def test_margin_specks_are_dropped_from_line_edges(self):
        cleaned = cleanup_ocr("e . ODWOŁANIE |\n\"Odwołujący: * i\n| 10-230 Olsztyn | ,\nOdbiór i i i . zagospodarowanie")
        self.assertEqual(
            cleaned.splitlines(),
            ["ODWOŁANIE", '"Odwołujący:', "10-230 Olsztyn", "Odbiór i zagospodarowanie"],
        )

    def test_misread_at_signs_are_repaired(self):
        cleaned = cleanup_ocr(
            "e-mail: m.wierzbickiawierzbicki-kancelaria.example\n"
            "e-mail: biuroQwierzbicki-kancelaria.cxample\n"
            "e-mail: d.kubiak(OQkubiak-kancelaria.example"
        )
        self.assertIn("m.wierzbicki@wierzbicki-kancelaria.example", cleaned)
        self.assertIn("biuro@wierzbicki-kancelaria.example", cleaned)
        self.assertIn("d.kubiak@kubiak-kancelaria.example", cleaned)

    def test_company_suffix_lookalikes(self):
        cleaned = cleanup_ocr("Orbisol Budownictwo Sp. Z 0.0.\nOlszewski 6 Partnerzy sp. K.")
        self.assertIn("Orbisol Budownictwo Sp. z o.o.", cleaned)
        self.assertIn("Olszewski & Partnerzy sp. k.", cleaned)

    def test_dot_leaders_do_not_glue_digits_onto_amounts(self):
        cleaned = cleanup_ocr("KWOTA PRZELEWU .......uuaaaaananaaaaaraaaraa+141111... 50,00 PLN")
        self.assertNotIn("141111", cleaned)
        self.assertIn("50,00 PLN", cleaned)

    def test_reference_codes_and_ted_lookalikes(self):
        cleaned = cleanup_ocr("przed KIO.w przetargu Dl.578.2026 €EN2605113961811")
        self.assertIn("KIO w przetargu DI.578.2026 CEN2605113961811", cleaned)
        self.assertEqual(ted_number("Dzienniku Urzędowym UE: 2026/8092-999328"), "999328-2026")
        self.assertEqual(ted_number("Unii Europejskiej nr 2026/5224429185"), "429185-2026")
        self.assertEqual(ted_number("2026/S 174-005431"), "005431-2026")


class ChecksumTests(unittest.TestCase):
    def test_valid_nrb_and_a_single_confusion(self):
        number = "60101010100081362231000000"
        self.assertTrue(nrb_ok(number))
        self.assertEqual(repair_nrb("6O" + number[2:]), number)
        self.assertEqual(repair_nrb("12345678901234567890123456"), "12345678901234567890123456")
        self.assertIsNone(repair_nrb("1234567890123456789012345X"))

    def test_ted_number_is_not_joined_like_a_nip(self):
        cleaned = cleanup_ocr("numer ogłoszenia TED: 999137-2026\nNIP 525-000-81-92")
        self.assertIn("999137-2026", cleaned)
        self.assertIn("5250008192", cleaned)

    def test_nip_checksum_and_impossible_date(self):
        self.assertTrue(nip_ok("9992956550"))
        self.assertIsNone(parse_date("2026-50-42"))
        self.assertEqual(parse_date("11.09.2026"), "2026-09-11")


if __name__ == "__main__":
    unittest.main()

"""OCR text is cleaned before extraction."""

import unittest

from checksums import nip_ok, nrb_ok, repair_nrb
from normalizers import parse_date
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


class ChecksumTests(unittest.TestCase):
    def test_valid_nrb_and_a_single_confusion(self):
        number = "60101010100081362231000000"
        self.assertTrue(nrb_ok(number))
        self.assertEqual(repair_nrb("6O" + number[2:]), number)
        self.assertIsNone(repair_nrb("12345678901234567890123456"))

    def test_nip_checksum_and_impossible_date(self):
        self.assertTrue(nip_ok("9992956550"))
        self.assertIsNone(parse_date("2026-50-42"))
        self.assertEqual(parse_date("11.09.2026"), "2026-09-11")


if __name__ == "__main__":
    unittest.main()

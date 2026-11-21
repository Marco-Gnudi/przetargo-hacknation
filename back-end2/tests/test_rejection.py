import unittest

from api import pdf_rejection


class PdfRejectionTests(unittest.TestCase):
    def test_a_named_pdf_with_header_is_accepted(self):
        self.assertIsNone(pdf_rejection("odwolanie.pdf", b"%PDF-1.7\n"))

    def test_wrong_extension_and_wrong_header_are_rejected(self):
        self.assertEqual(
            pdf_rejection("notes.txt", b"hello"),
            "Rejected: notes.txt – not a PDF",
        )
        self.assertEqual(
            pdf_rejection("odwolanie.pdf", b"not a pdf"),
            "Rejected: odwolanie.pdf – not a PDF",
        )


if __name__ == "__main__":
    unittest.main()

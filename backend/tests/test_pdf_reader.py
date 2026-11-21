from odwolania.config import task_data_dir
from odwolania.pdf_reader import read_pdf


def test_przyklad_01_pdfs_return_text():
    case = task_data_dir() / "dane" / "przyklad_01"
    pdfs = sorted(case.glob("*.pdf"))
    assert pdfs, f"no PDFs in {case}"
    for pdf in pdfs:
        text = read_pdf(pdf)
        assert text.strip(), pdf.name

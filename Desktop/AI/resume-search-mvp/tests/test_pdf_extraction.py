import pymupdf

from app.extraction.pdf import PdfTextExtractor


def _build_pdf_bytes(text: str | None = None) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def test_pdf_extractor_extracts_text_from_all_pages() -> None:
    document = pymupdf.open()
    first_page = document.new_page()
    first_page.insert_text((72, 72), "AI Engineer")
    second_page = document.new_page()
    second_page.insert_text((72, 72), "Python and FastAPI")
    pdf_bytes = document.tobytes()
    document.close()
    extractor = PdfTextExtractor()

    result = extractor.extract(pdf_bytes)

    assert result.status == "extracted"
    assert "AI Engineer" in result.text
    assert "Python and FastAPI" in result.text


def test_pdf_extractor_returns_empty_text_for_blank_pdf() -> None:
    extractor = PdfTextExtractor()

    result = extractor.extract(_build_pdf_bytes())

    assert result.status == "empty_text"
    assert result.text == ""


def test_pdf_extractor_returns_failed_for_invalid_pdf_bytes() -> None:
    extractor = PdfTextExtractor()

    result = extractor.extract(b"not a real pdf")

    assert result.status == "failed"
    assert result.text == ""

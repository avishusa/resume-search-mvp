from app.extraction.txt import TxtTextExtractor


def test_txt_extractor_decodes_utf8_text() -> None:
    extractor = TxtTextExtractor()

    result = extractor.extract("Senior Python Developer\nFastAPI experience".encode())

    assert result.status == "extracted"
    assert result.text == "Senior Python Developer\nFastAPI experience"


def test_txt_extractor_handles_utf8_bom() -> None:
    extractor = TxtTextExtractor()

    result = extractor.extract(b"\xef\xbb\xbfResume with BOM")

    assert result.status == "extracted"
    assert result.text == "Resume with BOM"


def test_txt_extractor_strips_extra_whitespace() -> None:
    extractor = TxtTextExtractor()

    result = extractor.extract(b"  AI Engineer  \r\n\r\n  Python  ")

    assert result.status == "extracted"
    assert result.text == "AI Engineer\nPython"


def test_txt_extractor_returns_empty_text_for_whitespace_only_file() -> None:
    extractor = TxtTextExtractor()

    result = extractor.extract(b"  \n\t  ")

    assert result.status == "empty_text"
    assert result.text == ""


def test_txt_extractor_returns_failed_for_invalid_utf8() -> None:
    extractor = TxtTextExtractor()

    result = extractor.extract(b"\xff\xfe\x00\x00")

    assert result.status == "failed"
    assert result.text == ""


def test_txt_extractor_does_not_return_not_implemented() -> None:
    extractor = TxtTextExtractor()

    result = extractor.extract(b"AI Engineer")

    assert result.status != "not_implemented"

from app.extraction.base import ExtractionResult


class PdfTextExtractor:
    def extract(self, file_bytes: bytes) -> ExtractionResult:
        try:
            import pymupdf

            with pymupdf.open(stream=file_bytes, filetype="pdf") as document:
                page_text = [page.get_text() for page in document]

            text = "\n".join(page_text)
            cleaned_text = "\n".join(
                line.strip() for line in text.splitlines() if line.strip()
            )

            if not cleaned_text:
                return ExtractionResult(text="", status="empty_text")

            return ExtractionResult(text=cleaned_text, status="extracted")
        except Exception:
            return ExtractionResult(text="", status="failed")

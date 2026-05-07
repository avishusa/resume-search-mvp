from app.extraction.base import ExtractionResult


class TxtTextExtractor:
    def extract(self, file_bytes: bytes) -> ExtractionResult:
        try:
            text = file_bytes.decode("utf-8-sig")
            cleaned_text = "\n".join(
                line.strip()
                for line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
                if line.strip()
            )

            if not cleaned_text:
                return ExtractionResult(text="", status="empty_text")

            return ExtractionResult(text=cleaned_text, status="extracted")
        except Exception:
            return ExtractionResult(text="", status="failed")

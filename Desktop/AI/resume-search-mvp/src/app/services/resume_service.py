from app.services.resume_ingestion_service import (
    ResumeIngestionService,
    UnsupportedResumeFileTypeError,
)
from app.schemas.resume import ResumeUploadResponse


class ResumeUploadService:
    def __init__(
        self,
        ingestion_service: ResumeIngestionService,
        preview_characters: int = 300,
    ) -> None:
        self._ingestion_service = ingestion_service
        self._preview_characters = preview_characters

    def upload_resume(
        self,
        file_name: str,
        mime_type: str | None,
        file_bytes: bytes,
    ) -> ResumeUploadResponse:
        record = self._ingestion_service.ingest_uploaded_file(
            file_name=file_name,
            mime_type=mime_type,
            file_bytes=file_bytes,
        )

        return ResumeUploadResponse(
            resume_id=record.resume_id,
            file_name=record.file_name,
            mime_type=record.mime_type,
            extraction_status=record.extraction_status,
            extracted_text_preview=record.extracted_text[: self._preview_characters],
        )

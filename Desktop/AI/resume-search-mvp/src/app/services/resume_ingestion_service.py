from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.extraction.base import TextExtractor
from app.extraction.docx import DocxTextExtractor
from app.extraction.pdf import PdfTextExtractor
from app.extraction.txt import TxtTextExtractor
from app.repositories.resume_repository import InMemoryResumeRepository, ResumeRecord
from app.schemas.resume import LocalDriveIngestionResponse, ResumeIngestionItem


class UnsupportedResumeFileTypeError(ValueError):
    pass


@dataclass(frozen=True)
class SupportedFileType:
    suffix: str
    mime_type: str


class ResumeIngestionService:
    def __init__(
        self,
        repository: InMemoryResumeRepository,
        local_drive_folder: Path | None = None,
        extractors: dict[str, TextExtractor] | None = None,
    ) -> None:
        self._repository = repository
        self._local_drive_folder = local_drive_folder or Path("data/drive_resumes")
        self._extractors = extractors or {
            "application/pdf": PdfTextExtractor(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxTextExtractor(),
            "text/plain": TxtTextExtractor(),
        }
        self._supported_file_types = {
            ".pdf": SupportedFileType(".pdf", "application/pdf"),
            ".docx": SupportedFileType(
                ".docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ".txt": SupportedFileType(".txt", "text/plain"),
        }

    def ingest_uploaded_file(
        self,
        file_name: str,
        mime_type: str | None,
        file_bytes: bytes,
    ) -> ResumeRecord:
        normalized_mime_type = mime_type or self._mime_type_from_file_name(file_name)
        if normalized_mime_type not in self._extractors:
            raise UnsupportedResumeFileTypeError(
                "Only PDF, DOCX, and TXT files are supported."
            )

        return self._create_resume_record(
            file_name=file_name,
            source_path=None,
            mime_type=normalized_mime_type,
            file_bytes=file_bytes,
        )

    def ingest_local_drive(self) -> LocalDriveIngestionResponse:
        total_files_seen = 0
        ingested_count = 0
        skipped_count = 0
        failed_count = 0
        resumes: list[ResumeIngestionItem] = []

        if not self._local_drive_folder.exists():
            return LocalDriveIngestionResponse(
                total_files_seen=0,
                ingested_count=0,
                skipped_count=0,
                failed_count=0,
                resumes=[],
            )

        for path in sorted(self._local_drive_folder.iterdir()):
            if not path.is_file():
                continue

            total_files_seen += 1
            file_type = self._supported_file_types.get(path.suffix.lower())
            if file_type is None:
                skipped_count += 1
                continue

            source_path = str(path.resolve())
            existing_record = self._repository.get_by_source_path(source_path)
            if existing_record is not None:
                skipped_count += 1
                resumes.append(self._to_ingestion_item(existing_record))
                continue

            try:
                record = self._create_resume_record(
                    file_name=path.name,
                    source_path=source_path,
                    mime_type=file_type.mime_type,
                    file_bytes=path.read_bytes(),
                )
            except Exception:
                failed_count += 1
                continue

            ingested_count += 1
            resumes.append(self._to_ingestion_item(record))

        return LocalDriveIngestionResponse(
            total_files_seen=total_files_seen,
            ingested_count=ingested_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            resumes=resumes,
        )

    def _create_resume_record(
        self,
        file_name: str,
        source_path: str | None,
        mime_type: str,
        file_bytes: bytes,
    ) -> ResumeRecord:
        extractor = self._extractors[mime_type]
        extraction = extractor.extract(file_bytes)
        record = ResumeRecord(
            resume_id=str(uuid4()),
            file_name=file_name,
            source_path=source_path,
            mime_type=mime_type,
            extracted_text=extraction.text,
            extraction_status=extraction.status,
            ingested_at=datetime.now(UTC),
        )
        return self._repository.save(record)

    def _mime_type_from_file_name(self, file_name: str) -> str:
        file_type = self._supported_file_types.get(Path(file_name).suffix.lower())
        if file_type is None:
            return "application/octet-stream"
        return file_type.mime_type

    def _to_ingestion_item(self, record: ResumeRecord) -> ResumeIngestionItem:
        return ResumeIngestionItem(
            resume_id=record.resume_id,
            file_name=record.file_name,
            source_path=record.source_path,
            mime_type=record.mime_type,
            extraction_status=record.extraction_status,
            extracted_text_preview=record.extracted_text[:300],
        )

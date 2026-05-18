import hashlib
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
from app.services.candidate_profile_service import CandidateProfileService
from app.services.resume_batch_processor import ResumeBatchProcessor
from app.storage.local_folder import LocalFolderResumeStorageProvider


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
        candidate_profile_service: CandidateProfileService | None = None,
    ) -> None:
        self._repository = repository
        self._local_drive_folder = local_drive_folder or Path("data/drive_resumes")
        self._candidate_profile_service = candidate_profile_service
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

    def ingest_local_drive(self, force: bool = False) -> LocalDriveIngestionResponse:
        if self._candidate_profile_service is None:
            from app.parsing.rule_based import RuleBasedResumeParserProvider

            self._candidate_profile_service = CandidateProfileService(
                primary_parser=RuleBasedResumeParserProvider(),
                fallback_parser=RuleBasedResumeParserProvider(),
            )

        return ResumeBatchProcessor(
            repository=self._repository,
            candidate_profile_service=self._candidate_profile_service,
            storage_provider=LocalFolderResumeStorageProvider(self._local_drive_folder),
            extractors=self._extractors,
        ).process_local_drive(force=force)

    def _create_resume_record(
        self,
        file_name: str,
        source_path: str | None,
        mime_type: str,
        file_bytes: bytes,
    ) -> ResumeRecord:
        extractor = self._extractors[mime_type]
        extraction = extractor.extract(file_bytes)
        candidate_profile = None
        parsing_status = None
        parser_used = None
        parsing_error = None
        ollama_error = None
        ollama_raw_response_preview = None
        ollama_model = None
        parsed_at = None
        now = datetime.now(UTC)
        if extraction.status == "extracted" and self._candidate_profile_service:
            parse_result = self._candidate_profile_service.parse_with_metadata(
                extraction.text
            )
            candidate_profile = parse_result.profile
            parsing_status = candidate_profile.parsing_status
            parser_used = candidate_profile.parser_used
            parsing_error = parse_result.parsing_error
            ollama_error = parse_result.ollama_error
            ollama_raw_response_preview = parse_result.ollama_raw_response_preview
            ollama_model = parse_result.ollama_model
            parsed_at = now
        elif extraction.status != "extracted":
            parsing_status = "failed"
            parsing_error = f"Parsing skipped because extraction_status={extraction.status}."
            ollama_error = parsing_error

        record = ResumeRecord(
            resume_id=str(uuid4()),
            provider_name="upload",
            source_id=None,
            file_name=file_name,
            source_path=source_path,
            file_type=mime_type,
            file_hash=hashlib.sha256(file_bytes).hexdigest(),
            last_modified=None,
            extraction_status=extraction.status,
            parsing_status=parsing_status,
            parser_used=parser_used,
            parsing_error=parsing_error,
            ollama_error=ollama_error,
            ollama_raw_response_preview=ollama_raw_response_preview,
            ollama_model=ollama_model,
            extracted_text=extraction.text,
            parsed_at=parsed_at,
            ingested_at=now,
            candidate_profile=candidate_profile,
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
            provider_name=record.provider_name,
            source_id=record.source_id,
            file_name=record.file_name,
            source_path=record.source_path,
            file_type=record.file_type,
            file_hash=record.file_hash,
            last_modified=record.last_modified.isoformat()
            if record.last_modified
            else None,
            extraction_status=record.extraction_status,
            parsing_status=record.parsing_status,
            parser_used=record.parser_used,
            parsing_error=record.parsing_error,
            ollama_error=record.ollama_error,
            ollama_raw_response_preview=record.ollama_raw_response_preview,
            ollama_model=record.ollama_model,
            parsed_at=record.parsed_at.isoformat() if record.parsed_at else None,
            ingested_at=record.ingested_at.isoformat(),
            extracted_text_preview=record.extracted_text_preview,
        )

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


@dataclass(frozen=True)
class SupportedFileType:
    suffix: str
    mime_type: str


class ResumeBatchProcessor:
    def __init__(
        self,
        repository: InMemoryResumeRepository,
        candidate_profile_service: CandidateProfileService,
        local_drive_folder: Path | None = None,
        extractors: dict[str, TextExtractor] | None = None,
    ) -> None:
        self._repository = repository
        self._candidate_profile_service = candidate_profile_service
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

    def process_local_drive(self, force: bool = False) -> LocalDriveIngestionResponse:
        total_files_seen = 0
        ingested_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        parsed_count = 0
        fallback_count = 0
        resumes: list[ResumeIngestionItem] = []

        if not self._local_drive_folder.exists():
            return LocalDriveIngestionResponse(
                total_files_seen=0,
                ingested_count=0,
                updated_count=0,
                skipped_count=0,
                failed_count=0,
                parsed_count=0,
                fallback_count=0,
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
            try:
                file_bytes = path.read_bytes()
                file_hash = self._hash_file_bytes(file_bytes)
                last_modified = datetime.fromtimestamp(path.stat().st_mtime, UTC)
            except Exception:
                failed_count += 1
                continue

            existing_record = self._repository.get_by_source_path(source_path)
            if existing_record and existing_record.file_hash == file_hash and not force:
                skipped_count += 1
                resumes.append(self._to_ingestion_item(existing_record))
                continue

            is_update = existing_record is not None
            record = self._process_file(
                resume_id=existing_record.resume_id if existing_record else str(uuid4()),
                file_name=path.name,
                source_path=source_path,
                file_type=file_type.mime_type,
                file_hash=file_hash,
                last_modified=last_modified,
                file_bytes=file_bytes,
                previous_ingested_at=existing_record.ingested_at
                if existing_record
                else None,
            )

            if record.extraction_status == "failed":
                failed_count += 1
            elif is_update:
                updated_count += 1
            else:
                ingested_count += 1

            if record.candidate_profile is not None:
                parsed_count += 1
            if record.parser_used == "rule_based" and record.parsing_error:
                fallback_count += 1

            resumes.append(self._to_ingestion_item(record))

        return LocalDriveIngestionResponse(
            total_files_seen=total_files_seen,
            ingested_count=ingested_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            parsed_count=parsed_count,
            fallback_count=fallback_count,
            resumes=resumes,
        )

    def _process_file(
        self,
        resume_id: str,
        file_name: str,
        source_path: str,
        file_type: str,
        file_hash: str,
        last_modified: datetime,
        file_bytes: bytes,
        previous_ingested_at: datetime | None,
    ) -> ResumeRecord:
        now = datetime.now(UTC)
        extractor = self._extractors[file_type]
        extraction = extractor.extract(file_bytes)
        candidate_profile = None
        parsing_status = None
        parser_used = None
        parsing_error = None
        ollama_error = None
        ollama_raw_response_preview = None
        ollama_model = None
        parsed_at = None

        if extraction.status == "extracted":
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
        else:
            parsing_status = "failed"
            parsing_error = f"Parsing skipped because extraction_status={extraction.status}."
            ollama_error = parsing_error

        record = ResumeRecord(
            resume_id=resume_id,
            file_name=file_name,
            source_path=source_path,
            file_type=file_type,
            file_hash=file_hash,
            last_modified=last_modified,
            extraction_status=extraction.status,
            parsing_status=parsing_status,
            parser_used=parser_used,
            parsing_error=parsing_error,
            ollama_error=ollama_error,
            ollama_raw_response_preview=ollama_raw_response_preview,
            ollama_model=ollama_model,
            extracted_text=extraction.text,
            parsed_at=parsed_at,
            ingested_at=previous_ingested_at or now,
            candidate_profile=candidate_profile,
        )
        return self._repository.save(record)

    def _hash_file_bytes(self, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    def _to_ingestion_item(self, record: ResumeRecord) -> ResumeIngestionItem:
        return ResumeIngestionItem(
            resume_id=record.resume_id,
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


def run_nightly_resume_batch(
    batch_processor: ResumeBatchProcessor,
) -> LocalDriveIngestionResponse:
    return batch_processor.process_local_drive()

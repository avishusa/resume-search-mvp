import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from app.extraction.base import TextExtractor
from app.extraction.docx import DocxTextExtractor
from app.extraction.pdf import PdfTextExtractor
from app.extraction.txt import TxtTextExtractor
from app.repositories.resume_repository import InMemoryResumeRepository, ResumeRecord
from app.schemas.resume import (
    LocalDriveIngestionResponse,
    ProviderIngestionSummary,
    ResumeIngestionItem,
)
from app.services.candidate_profile_service import CandidateProfileService
from app.storage.base import ResumeFileReference, ResumeStorageProvider
from app.storage.local_folder import LocalFolderResumeStorageProvider


class ResumeBatchProcessor:
    def __init__(
        self,
        repository: InMemoryResumeRepository,
        candidate_profile_service: CandidateProfileService,
        storage_provider: ResumeStorageProvider | None = None,
        storage_providers: list[ResumeStorageProvider] | None = None,
        extractors: dict[str, TextExtractor] | None = None,
    ) -> None:
        self._repository = repository
        self._candidate_profile_service = candidate_profile_service
        self._storage_provider = storage_provider or LocalFolderResumeStorageProvider(
            "data/drive_resumes"
        )
        self._storage_providers = storage_providers
        self._extractors = extractors or {
            "application/pdf": PdfTextExtractor(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxTextExtractor(),
            "text/plain": TxtTextExtractor(),
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
        provider_summaries: list[ProviderIngestionSummary] = []

        for provider in self._get_storage_providers():
            provider_summary = self._process_provider(
                provider=provider,
                force=force,
                resumes=resumes,
            )
            provider_summaries.append(provider_summary)
            total_files_seen += provider_summary.total_files_seen
            ingested_count += provider_summary.ingested_count
            updated_count += provider_summary.updated_count
            skipped_count += provider_summary.skipped_count
            failed_count += provider_summary.failed_count
            parsed_count += provider_summary.parsed_count
            fallback_count += provider_summary.fallback_count

        return LocalDriveIngestionResponse(
            total_files_seen=total_files_seen,
            ingested_count=ingested_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            parsed_count=parsed_count,
            fallback_count=fallback_count,
            resumes=resumes,
            providers=provider_summaries,
        )

    def _get_storage_providers(self) -> list[ResumeStorageProvider]:
        if self._storage_providers is None:
            return [self._storage_provider]
        if len(self._storage_providers) == 1:
            return [self._storage_provider]
        return self._storage_providers

    def _process_provider(
        self,
        provider: ResumeStorageProvider,
        force: bool,
        resumes: list[ResumeIngestionItem],
    ) -> ProviderIngestionSummary:
        total_files_seen = 0
        ingested_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        parsed_count = 0
        fallback_count = 0

        try:
            file_references = provider.list_resume_files()
        except Exception as exception:
            return ProviderIngestionSummary(
                provider_name=provider.provider_name,
                total_files_seen=0,
                ingested_count=0,
                updated_count=0,
                skipped_count=0,
                failed_count=1,
                parsed_count=0,
                fallback_count=0,
                error_message=str(exception),
            )

        for file_reference in file_references:
            total_files_seen += 1
            try:
                file_bytes = provider.read_file(file_reference)
                file_hash = self._hash_file_bytes(file_bytes)
            except Exception:
                failed_count += 1
                continue

            existing_record = self._get_existing_record(file_reference)
            if existing_record and existing_record.file_hash == file_hash and not force:
                skipped_count += 1
                resumes.append(self._to_ingestion_item(existing_record))
                continue

            is_update = existing_record is not None
            record = self._process_file(
                resume_id=existing_record.resume_id if existing_record else str(uuid4()),
                file_reference=file_reference,
                file_hash=file_hash,
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

        return ProviderIngestionSummary(
            provider_name=provider.provider_name,
            total_files_seen=total_files_seen,
            ingested_count=ingested_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            parsed_count=parsed_count,
            fallback_count=fallback_count,
        )

    def _get_existing_record(
        self,
        file_reference: ResumeFileReference,
    ) -> ResumeRecord | None:
        if file_reference.source_id and hasattr(
            self._repository,
            "get_by_provider_and_source_id",
        ):
            record = self._repository.get_by_provider_and_source_id(
                file_reference.provider_name,
                file_reference.source_id,
            )
            if record is not None:
                return record
            legacy_record = self._repository.get_by_source_path(
                file_reference.source_path
            )
            if legacy_record is not None and legacy_record.source_id is None:
                return legacy_record
            return None
        return self._repository.get_by_source_path(file_reference.source_path)

    def _process_file(
        self,
        resume_id: str,
        file_reference: ResumeFileReference,
        file_hash: str,
        file_bytes: bytes,
        previous_ingested_at: datetime | None,
    ) -> ResumeRecord:
        now = datetime.now(UTC)
        extractor = self._extractors[file_reference.file_type]
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
            provider_name=file_reference.provider_name,
            source_id=file_reference.source_id,
            file_name=file_reference.file_name,
            source_path=file_reference.source_path,
            file_type=file_reference.file_type,
            file_hash=file_hash,
            last_modified=file_reference.last_modified,
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


def run_nightly_resume_batch(
    batch_processor: ResumeBatchProcessor,
) -> LocalDriveIngestionResponse:
    return batch_processor.process_local_drive()

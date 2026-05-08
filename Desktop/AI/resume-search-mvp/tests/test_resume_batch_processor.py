from app.parsing.base import ResumeParserError
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.repositories.resume_repository import InMemoryResumeRepository
from app.schemas.candidate import CandidateProfile
from app.services.candidate_profile_service import CandidateProfileService
from app.services.resume_batch_processor import ResumeBatchProcessor
from app.storage.local_folder import LocalFolderResumeStorageProvider
from app.storage.base import ResumeFileReference
from datetime import UTC, datetime


class FailingPrimaryParser:
    parser_name = "ollama"

    def __init__(self, message: str = "timeout") -> None:
        self._message = message

    def parse(self, resume_text: str) -> CandidateProfile:
        raise ResumeParserError(self._message)


def _rule_based_profile_service() -> CandidateProfileService:
    parser = RuleBasedResumeParserProvider(skill_catalog=["Python", "FastAPI"])
    return CandidateProfileService(primary_parser=parser, fallback_parser=parser)


def test_batch_processor_skips_unchanged_file_on_second_ingestion(tmp_path) -> None:
    (tmp_path / "ai-engineer.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    repository = InMemoryResumeRepository()
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_rule_based_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(tmp_path),
    )

    first_response = processor.process_local_drive()
    second_response = processor.process_local_drive()

    assert first_response.ingested_count == 1
    assert second_response.ingested_count == 0
    assert second_response.updated_count == 0
    assert second_response.skipped_count == 1
    assert len(repository.list_all()) == 1


def test_batch_processor_reprocesses_changed_file(tmp_path) -> None:
    resume_path = tmp_path / "ai-engineer.txt"
    resume_path.write_text("AI Engineer\nPython", encoding="utf-8")
    repository = InMemoryResumeRepository()
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_rule_based_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(tmp_path),
    )

    first_response = processor.process_local_drive()
    first_resume_id = repository.list_all()[0].resume_id
    first_hash = repository.list_all()[0].file_hash
    resume_path.write_text("AI Engineer\nPython FastAPI", encoding="utf-8")
    second_response = processor.process_local_drive()

    assert first_response.ingested_count == 1
    assert second_response.updated_count == 1
    assert repository.list_all()[0].resume_id == first_resume_id
    assert repository.list_all()[0].file_hash != first_hash
    assert "FastAPI" in repository.list_all()[0].extracted_text


def test_batch_processor_force_reprocesses_existing_unchanged_file(tmp_path) -> None:
    (tmp_path / "ai-engineer.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    repository = InMemoryResumeRepository()
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_rule_based_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(tmp_path),
    )

    first_response = processor.process_local_drive()
    second_response = processor.process_local_drive(force=True)

    assert first_response.ingested_count == 1
    assert second_response.ingested_count == 0
    assert second_response.updated_count == 1
    assert second_response.skipped_count == 0
    assert len(repository.list_all()) == 1


def test_batch_processor_records_ollama_error_when_falling_back(tmp_path) -> None:
    (tmp_path / "ai-engineer.txt").write_text(
        "AI Engineer\njane@example.com\nPython",
        encoding="utf-8",
    )
    repository = InMemoryResumeRepository()
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=CandidateProfileService(
            primary_parser=FailingPrimaryParser("timeout from ollama"),
            fallback_parser=RuleBasedResumeParserProvider(skill_catalog=["Python"]),
        ),
        storage_provider=LocalFolderResumeStorageProvider(tmp_path),
    )

    response = processor.process_local_drive()
    record = repository.list_all()[0]

    assert response.parsed_count == 1
    assert response.fallback_count == 1
    assert record.parser_used == "rule_based"
    assert record.parsing_error == "timeout from ollama"


def test_batch_processor_continues_when_one_resume_extraction_fails(tmp_path) -> None:
    (tmp_path / "good-resume.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    (tmp_path / "broken-resume.pdf").write_bytes(b"not a real pdf")
    repository = InMemoryResumeRepository()
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_rule_based_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(tmp_path),
    )

    response = processor.process_local_drive()
    records_by_file_name = {record.file_name: record for record in repository.list_all()}

    assert response.total_files_seen == 2
    assert response.ingested_count == 1
    assert response.failed_count == 1
    assert records_by_file_name["good-resume.txt"].extraction_status == "extracted"
    assert records_by_file_name["broken-resume.pdf"].extraction_status == "failed"


class FakeStorageProvider:
    provider_name = "fake"

    def __init__(self) -> None:
        self.read_called = False
        self._reference = ResumeFileReference(
            source_id="fake-1",
            source_path="fake://resume.txt",
            file_name="resume.txt",
            file_type="text/plain",
            last_modified=datetime.now(UTC),
            size_bytes=18,
            provider_name=self.provider_name,
        )

    def list_resume_files(self) -> list[ResumeFileReference]:
        return [self._reference]

    def read_file(self, file_reference: ResumeFileReference) -> bytes:
        self.read_called = True
        return b"AI Engineer\nPython"


def test_batch_processor_uses_storage_provider_abstraction() -> None:
    repository = InMemoryResumeRepository()
    storage_provider = FakeStorageProvider()
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_rule_based_profile_service(),
        storage_provider=storage_provider,
    )

    response = processor.process_local_drive()

    assert storage_provider.read_called is True
    assert response.ingested_count == 1
    assert repository.list_all()[0].source_path == "fake://resume.txt"

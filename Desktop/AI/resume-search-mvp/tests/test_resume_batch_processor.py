from app.parsing.base import ResumeParserError
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.repositories.resume_repository import InMemoryResumeRepository
from app.schemas.candidate import CandidateProfile
from app.services.candidate_profile_service import CandidateProfileService
from app.services.resume_batch_processor import ResumeBatchProcessor
from app.storage.local_folder import LocalFolderResumeStorageProvider
from app.storage.base import ResumeFileReference
from datetime import UTC, datetime
from threading import Lock
from time import sleep


class FailingPrimaryParser:
    parser_name = "ollama"

    def __init__(self, message: str = "timeout") -> None:
        self._message = message

    def parse(self, resume_text: str) -> CandidateProfile:
        raise ResumeParserError(self._message)


class TrackingParser:
    parser_name = "ollama"

    def __init__(self) -> None:
        self.current_calls = 0
        self.max_concurrent_calls = 0
        self._lock = Lock()

    def parse(self, resume_text: str) -> CandidateProfile:
        with self._lock:
            self.current_calls += 1
            self.max_concurrent_calls = max(
                self.max_concurrent_calls,
                self.current_calls,
            )
        sleep(0.05)
        with self._lock:
            self.current_calls -= 1

        return CandidateProfile(
            candidate_name="Jane Candidate",
            email="jane@example.com",
            phone=None,
            current_title="AI Engineer",
            skills=["Python"],
            total_experience_years=None,
            companies=[],
            education=[],
            resume_summary="AI Engineer.",
            confidence_score=0.8,
            parsing_status="parsed",
            parser_used="ollama",
        )


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


def test_batch_processor_does_not_exceed_configured_parse_concurrency(tmp_path) -> None:
    for index in range(4):
        (tmp_path / f"resume-{index}.txt").write_text(
            "AI Engineer\nPython",
            encoding="utf-8",
        )
    tracking_parser = TrackingParser()
    repository = InMemoryResumeRepository()
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=CandidateProfileService(
            primary_parser=tracking_parser,
            fallback_parser=RuleBasedResumeParserProvider(skill_catalog=["Python"]),
        ),
        storage_provider=LocalFolderResumeStorageProvider(tmp_path),
        parse_concurrency=2,
    )

    response = processor.process_local_drive()

    assert response.ingested_count == 4
    assert response.configured_concurrency == 2
    assert tracking_parser.max_concurrent_calls <= 2
    assert tracking_parser.max_concurrent_calls > 1
    assert response.max_observed_parallel_tasks <= 2
    assert response.max_observed_parallel_tasks > 1
    assert len([resume.task_id for resume in response.resumes if resume.task_id]) == 4


def test_batch_processor_reports_single_parallel_task_when_concurrency_is_one(
    tmp_path,
) -> None:
    for index in range(2):
        (tmp_path / f"resume-{index}.txt").write_text(
            "AI Engineer\nPython",
            encoding="utf-8",
        )
    tracking_parser = TrackingParser()
    repository = InMemoryResumeRepository()
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=CandidateProfileService(
            primary_parser=tracking_parser,
            fallback_parser=RuleBasedResumeParserProvider(skill_catalog=["Python"]),
        ),
        storage_provider=LocalFolderResumeStorageProvider(tmp_path),
        parse_concurrency=1,
    )

    response = processor.process_local_drive()

    assert response.ingested_count == 2
    assert response.configured_concurrency == 1
    assert response.max_observed_parallel_tasks == 1
    assert tracking_parser.max_concurrent_calls == 1


def test_batch_processor_reports_per_resume_timing_diagnostics(tmp_path) -> None:
    (tmp_path / "resume.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    repository = InMemoryResumeRepository()
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_rule_based_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(tmp_path),
    )

    response = processor.process_local_drive()
    resume = response.resumes[0]

    assert response.total_batch_duration_seconds is not None
    assert resume.processing_started_at is not None
    assert resume.processing_finished_at is not None
    assert resume.parsing_started_at is not None
    assert resume.parsing_finished_at is not None
    assert resume.parsing_duration_seconds is not None
    assert resume.task_id == 1
    assert resume.worker_slot


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

    def __init__(
        self,
        provider_name: str = "fake",
        source_id: str = "fake-1",
        source_path: str = "fake://resume.txt",
        file_name: str = "resume.txt",
        file_bytes: bytes = b"AI Engineer\nPython",
    ) -> None:
        self.provider_name = provider_name
        self._file_bytes = file_bytes
        self.read_called = False
        self._reference = ResumeFileReference(
            source_id=source_id,
            source_path=source_path,
            file_name=file_name,
            file_type="text/plain",
            last_modified=datetime.now(UTC),
            size_bytes=len(file_bytes),
            provider_name=self.provider_name,
        )

    def list_resume_files(self) -> list[ResumeFileReference]:
        return [self._reference]

    def read_file(self, file_reference: ResumeFileReference) -> bytes:
        self.read_called = True
        return self._file_bytes


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


def test_batch_processor_processes_files_from_multiple_providers() -> None:
    repository = InMemoryResumeRepository()
    local_provider = FakeStorageProvider(
        provider_name="local",
        source_id="/fake/local/resume.txt",
        source_path="/fake/local/resume.txt",
        file_name="local-resume.txt",
        file_bytes=b"AI Engineer\nPython",
    )
    google_provider = FakeStorageProvider(
        provider_name="google_drive",
        source_id="drive-file-1",
        source_path="google_drive://drive-file-1",
        file_name="google-resume.txt",
        file_bytes=b"AI Engineer\nFastAPI",
    )
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_rule_based_profile_service(),
        storage_provider=local_provider,
        storage_providers=[local_provider, google_provider],
    )

    response = processor.process_local_drive()

    assert response.total_files_seen == 2
    assert response.ingested_count == 2
    assert [summary.provider_name for summary in response.providers] == [
        "local",
        "google_drive",
    ]
    assert {record.provider_name for record in repository.list_all()} == {
        "local",
        "google_drive",
    }


def test_batch_processor_identity_uses_provider_and_source_id() -> None:
    repository = InMemoryResumeRepository()
    local_provider = FakeStorageProvider(
        provider_name="local",
        source_id="/fake/resume.txt",
        source_path="/fake/resume.txt",
        file_name="same-name.txt",
        file_bytes=b"AI Engineer\nPython",
    )
    google_provider = FakeStorageProvider(
        provider_name="google_drive",
        source_id="drive-file-1",
        source_path="google_drive://drive-file-1",
        file_name="same-name.txt",
        file_bytes=b"AI Engineer\nPython",
    )
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_rule_based_profile_service(),
        storage_provider=local_provider,
        storage_providers=[local_provider, google_provider],
    )

    first_response = processor.process_local_drive()
    second_response = processor.process_local_drive()

    assert first_response.ingested_count == 2
    assert second_response.skipped_count == 2
    assert len(repository.list_all()) == 2
    assert {
        (record.provider_name, record.source_id, record.file_name)
        for record in repository.list_all()
    } == {
        ("local", "/fake/resume.txt", "same-name.txt"),
        ("google_drive", "drive-file-1", "same-name.txt"),
    }

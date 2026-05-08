from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.database import Base
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.repositories.batch_run_repository import BatchRunRepository
from app.repositories.sqlalchemy_resume_repository import SQLAlchemyResumeRepository
from app.schemas.resume import LocalDriveIngestionResponse
from app.services.batch_processing_service import (
    BatchAlreadyRunningError,
    ResumeBatchProcessingService,
)
from app.services.candidate_profile_service import CandidateProfileService
from app.services.resume_batch_processor import ResumeBatchProcessor
from app.storage.local_folder import LocalFolderResumeStorageProvider


class FakeBatchProcessor:
    def __init__(self, summary: LocalDriveIngestionResponse) -> None:
        self._summary = summary

    def process_local_drive(self, force: bool = False) -> LocalDriveIngestionResponse:
        return self._summary


def _session_factory(tmp_path: Path, name: str = "batch_service.db"):
    engine = create_engine(
        f"sqlite:///{tmp_path / name}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _repositories(tmp_path: Path):
    session_factory = _session_factory(tmp_path)
    return (
        SQLAlchemyResumeRepository(session_factory=session_factory),
        BatchRunRepository(session_factory=session_factory),
    )


def _profile_service() -> CandidateProfileService:
    parser = RuleBasedResumeParserProvider(skill_catalog=["Python", "FastAPI"])
    return CandidateProfileService(primary_parser=parser, fallback_parser=parser)


def test_batch_run_record_is_created_and_completed_with_counts(tmp_path) -> None:
    _resume_repository, batch_run_repository = _repositories(tmp_path)
    summary = LocalDriveIngestionResponse(
        total_files_seen=3,
        ingested_count=1,
        updated_count=1,
        skipped_count=1,
        failed_count=0,
        parsed_count=2,
        fallback_count=0,
        resumes=[],
    )
    service = ResumeBatchProcessingService(
        batch_processor=FakeBatchProcessor(summary),
        batch_run_repository=batch_run_repository,
    )

    batch_run, returned_summary = service.run_local_drive_batch()

    persisted_run = batch_run_repository.get(batch_run.batch_id)
    assert returned_summary == summary
    assert persisted_run.status == "completed"
    assert persisted_run.finished_at is not None
    assert persisted_run.total_files_seen == 3
    assert persisted_run.ingested_count == 1
    assert persisted_run.updated_count == 1
    assert persisted_run.skipped_count == 1
    assert persisted_run.parsed_count == 2


def test_batch_service_skips_unchanged_file(tmp_path) -> None:
    resume_repository, batch_run_repository = _repositories(tmp_path)
    drive_folder = tmp_path / "drive"
    drive_folder.mkdir()
    (drive_folder / "resume.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    processor = ResumeBatchProcessor(
        repository=resume_repository,
        candidate_profile_service=_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(drive_folder),
    )
    service = ResumeBatchProcessingService(processor, batch_run_repository)

    service.run_local_drive_batch()
    _batch_run, second_summary = service.run_local_drive_batch()

    assert second_summary.skipped_count == 1
    assert second_summary.ingested_count == 0


def test_batch_service_updates_changed_file(tmp_path) -> None:
    resume_repository, batch_run_repository = _repositories(tmp_path)
    drive_folder = tmp_path / "drive"
    drive_folder.mkdir()
    resume_path = drive_folder / "resume.txt"
    resume_path.write_text("AI Engineer\nPython", encoding="utf-8")
    processor = ResumeBatchProcessor(
        repository=resume_repository,
        candidate_profile_service=_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(drive_folder),
    )
    service = ResumeBatchProcessingService(processor, batch_run_repository)

    service.run_local_drive_batch()
    resume_path.write_text("AI Engineer\nPython FastAPI", encoding="utf-8")
    _batch_run, second_summary = service.run_local_drive_batch()

    assert second_summary.updated_count == 1
    assert len(resume_repository.list_all()) == 1


def test_batch_service_failed_file_increments_failed_count(tmp_path) -> None:
    resume_repository, batch_run_repository = _repositories(tmp_path)
    drive_folder = tmp_path / "drive"
    drive_folder.mkdir()
    (drive_folder / "good.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    (drive_folder / "broken.pdf").write_bytes(b"not a pdf")
    processor = ResumeBatchProcessor(
        repository=resume_repository,
        candidate_profile_service=_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(drive_folder),
    )
    service = ResumeBatchProcessingService(processor, batch_run_repository)

    batch_run, summary = service.run_local_drive_batch()

    persisted_run = batch_run_repository.get(batch_run.batch_id)
    assert summary.failed_count == 1
    assert persisted_run.failed_count == 1
    assert persisted_run.status == "completed"


def test_batch_service_rejects_overlapping_run(tmp_path) -> None:
    _resume_repository, batch_run_repository = _repositories(tmp_path)
    service = ResumeBatchProcessingService(
        batch_processor=FakeBatchProcessor(
            LocalDriveIngestionResponse(
                total_files_seen=0,
                ingested_count=0,
                updated_count=0,
                skipped_count=0,
                failed_count=0,
                parsed_count=0,
                fallback_count=0,
                resumes=[],
            )
        ),
        batch_run_repository=batch_run_repository,
    )
    service._lock.acquire()

    try:
        with pytest.raises(BatchAlreadyRunningError):
            service.run_local_drive_batch()
    finally:
        service._lock.release()


def test_nightly_scheduler_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_NIGHTLY_BATCH", raising=False)

    assert Settings().enable_nightly_batch is False

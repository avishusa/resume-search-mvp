from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.repositories.sqlalchemy_resume_repository import SQLAlchemyResumeRepository
from app.services.candidate_profile_service import CandidateProfileService
from app.services.resume_batch_processor import ResumeBatchProcessor
from app.storage.local_folder import LocalFolderResumeStorageProvider


def _repository(tmp_path: Path) -> SQLAlchemyResumeRepository:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'batch.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SQLAlchemyResumeRepository(session_factory=session_factory)


def _profile_service() -> CandidateProfileService:
    parser = RuleBasedResumeParserProvider(skill_catalog=["Python", "FastAPI"])
    return CandidateProfileService(primary_parser=parser, fallback_parser=parser)


def test_same_file_hash_is_skipped_on_second_sqlite_ingestion(tmp_path) -> None:
    drive_folder = tmp_path / "drive"
    drive_folder.mkdir()
    (drive_folder / "resume.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    repository = _repository(tmp_path)
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(drive_folder),
    )

    first_response = processor.process_local_drive()
    second_response = processor.process_local_drive()

    assert first_response.ingested_count == 1
    assert second_response.skipped_count == 1
    assert len(repository.list_all()) == 1


def test_changed_file_hash_updates_sqlite_record(tmp_path) -> None:
    drive_folder = tmp_path / "drive"
    drive_folder.mkdir()
    resume_path = drive_folder / "resume.txt"
    resume_path.write_text("AI Engineer\nPython", encoding="utf-8")
    repository = _repository(tmp_path)
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(drive_folder),
    )

    processor.process_local_drive()
    first_hash = repository.list_all()[0].file_hash
    resume_path.write_text("AI Engineer\nPython FastAPI", encoding="utf-8")
    second_response = processor.process_local_drive()

    assert second_response.updated_count == 1
    assert len(repository.list_all()) == 1
    assert repository.list_all()[0].file_hash != first_hash


def test_force_reprocesses_unchanged_sqlite_record(tmp_path) -> None:
    drive_folder = tmp_path / "drive"
    drive_folder.mkdir()
    (drive_folder / "resume.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    repository = _repository(tmp_path)
    processor = ResumeBatchProcessor(
        repository=repository,
        candidate_profile_service=_profile_service(),
        storage_provider=LocalFolderResumeStorageProvider(drive_folder),
    )

    processor.process_local_drive()
    second_response = processor.process_local_drive(force=True)

    assert second_response.updated_count == 1
    assert second_response.skipped_count == 0
    assert len(repository.list_all()) == 1

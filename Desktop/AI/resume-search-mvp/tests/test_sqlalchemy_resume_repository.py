from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.repositories.resume_repository import ResumeRecord
from app.repositories.sqlalchemy_resume_repository import SQLAlchemyResumeRepository
from app.schemas.candidate import CandidateProfile


def _repository(tmp_path) -> SQLAlchemyResumeRepository:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test_resume_search.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SQLAlchemyResumeRepository(session_factory=session_factory)


def _record(
    resume_id: str = "resume-1",
    source_path: str = "/fake/resume.txt",
    file_hash: str = "hash-1",
    provider_name: str = "local",
    source_id: str = "/fake/resume.txt",
) -> ResumeRecord:
    now = datetime.now(UTC)
    return ResumeRecord(
        resume_id=resume_id,
        provider_name=provider_name,
        source_id=source_id,
        file_name="resume.txt",
        source_path=source_path,
        file_type="text/plain",
        file_hash=file_hash,
        last_modified=now,
        extraction_status="extracted",
        parsing_status="parsed",
        parser_used="ollama",
        parsing_error=None,
        ollama_error=None,
        ollama_raw_response_preview=None,
        ollama_model="llama3.1:8b",
        extracted_text="AI Engineer\nPython",
        parsed_at=now,
        ingested_at=now,
        candidate_profile=CandidateProfile(
            candidate_name="Jane Candidate",
            email="jane@example.com",
            phone=None,
            current_title="AI Engineer",
            skills=["Python"],
            total_experience_years=6,
            companies=["Acme"],
            education=["BS Computer Science"],
            resume_summary="AI Engineer",
            confidence_score=0.9,
            parsing_status="parsed",
            parser_used="ollama",
        ),
    )


def test_resume_record_can_be_inserted_and_listed(tmp_path) -> None:
    repository = _repository(tmp_path)

    repository.save(_record())

    resumes = repository.list_all()
    assert len(resumes) == 1
    assert resumes[0].candidate_profile.email == "jane@example.com"
    assert resumes[0].candidate_profile.skills == ["Python"]


def test_get_by_source_path_and_file_hash(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.save(_record(file_hash="abc123"))

    matching_record = repository.get_by_source_path_and_file_hash(
        "/fake/resume.txt",
        "abc123",
    )
    missing_record = repository.get_by_source_path_and_file_hash(
        "/fake/resume.txt",
        "different",
    )

    assert matching_record is not None
    assert missing_record is None


def test_upsert_updates_existing_resume_by_source_path(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.save(_record(resume_id="old-id", file_hash="old"))
    repository.upsert_by_source_path(_record(resume_id="old-id", file_hash="new"))

    resumes = repository.list_all()
    assert len(resumes) == 1
    assert resumes[0].file_hash == "new"


def test_upsert_uses_provider_name_and_source_id_identity(tmp_path) -> None:
    repository = _repository(tmp_path)
    repository.save(
        _record(
            resume_id="local-id",
            provider_name="local",
            source_id="/fake/resume.txt",
            source_path="/fake/resume.txt",
        )
    )
    repository.save(
        _record(
            resume_id="drive-id",
            provider_name="google_drive",
            source_id="drive-file-1",
            source_path="google_drive://drive-file-1",
        )
    )

    local_record = repository.get_by_provider_and_source_id(
        "local",
        "/fake/resume.txt",
    )
    drive_record = repository.get_by_provider_and_source_id(
        "google_drive",
        "drive-file-1",
    )

    assert len(repository.list_all()) == 2
    assert local_record.resume_id == "local-id"
    assert drive_record.resume_id == "drive-id"


def test_repository_recreated_with_same_database_keeps_data(tmp_path) -> None:
    database_path = tmp_path / "restart.db"
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    first_repository = SQLAlchemyResumeRepository(session_factory=session_factory)
    first_repository.save(_record())

    second_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    second_session_factory = sessionmaker(
        bind=second_engine,
        autoflush=False,
        autocommit=False,
    )
    second_repository = SQLAlchemyResumeRepository(
        session_factory=second_session_factory,
    )

    assert len(second_repository.list_all()) == 1
    assert second_repository.list_all()[0].resume_id == "resume-1"

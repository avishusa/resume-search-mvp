from fastapi.testclient import TestClient
from datetime import UTC, datetime

from app.container import (
    batch_processing_service,
    local_resume_batch_processor,
    resume_repository,
)
from app.main import create_app
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.repositories.resume_repository import ResumeRecord
from app.schemas.candidate import CandidateProfile
from app.services.candidate_profile_service import CandidateProfileService
from app.storage.local_folder import LocalFolderResumeStorageProvider


def _parsed_record(
    resume_id: str,
    file_name: str,
    years: float | None,
) -> ResumeRecord:
    now = datetime.now(UTC)
    return ResumeRecord(
        resume_id=resume_id,
        file_name=file_name,
        source_path=f"/fake/{file_name}",
        file_type="text/plain",
        file_hash=resume_id,
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
            candidate_name=file_name,
            email=f"{resume_id}@example.com",
            phone=None,
            current_title="AI Engineer",
            skills=["Python"],
            total_experience_years=years,
            companies=[],
            education=[],
            resume_summary="",
            confidence_score=0.9,
            parsing_status="parsed",
            parser_used="ollama",
        ),
    )


def test_search_jd_returns_only_strict_title_matched_resumes(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    monkeypatch.setattr(
        local_resume_batch_processor,
        "_storage_provider",
        LocalFolderResumeStorageProvider(tmp_path),
    )
    monkeypatch.setattr(
        local_resume_batch_processor,
        "_candidate_profile_service",
        CandidateProfileService(
            primary_parser=RuleBasedResumeParserProvider(),
            fallback_parser=RuleBasedResumeParserProvider(),
        ),
    )
    (tmp_path / "ai-engineer.txt").write_text(
        "AI Engineer\nPython LLM LangChain",
        encoding="utf-8",
    )
    (tmp_path / "data-scientist.txt").write_text(
        "Data Scientist\nPython statistics",
        encoding="utf-8",
    )
    client = TestClient(create_app())

    ingest_response = client.post("/resumes/ingest-local-drive")
    search_response = client.post(
        "/jobs/search",
        json={
            "job_title": "AI Engineer",
            "job_description": "Build AI features.",
            "required_skills": ["Python"],
            "nice_to_have_skills": ["LangChain"],
        },
    )

    assert ingest_response.status_code == 200
    assert search_response.status_code == 200
    body = search_response.json()
    assert body["query"]["job_title"] == "AI Engineer"
    assert body["total_candidates_considered"] == 2
    assert body["matched_count"] == 1
    results = body["results"]
    assert [result["file_name"] for result in results] == ["ai-engineer.txt"]
    assert results[0]["candidate_name"] is None
    assert results[0]["current_title"] == "AI Engineer"
    assert results[0]["matched_required_skills"] == ["Python"]


def test_search_ranks_candidates_with_more_required_skills_higher(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    monkeypatch.setattr(
        local_resume_batch_processor,
        "_storage_provider",
        LocalFolderResumeStorageProvider(tmp_path),
    )
    monkeypatch.setattr(
        local_resume_batch_processor,
        "_candidate_profile_service",
        CandidateProfileService(
            primary_parser=RuleBasedResumeParserProvider(),
            fallback_parser=RuleBasedResumeParserProvider(),
        ),
    )
    (tmp_path / "strong-ai-engineer.txt").write_text(
        "AI Engineer\nPython LLM LangChain Docker",
        encoding="utf-8",
    )
    (tmp_path / "weaker-ai-engineer.txt").write_text(
        "AI Engineer\nPython",
        encoding="utf-8",
    )
    client = TestClient(create_app())

    client.post("/resumes/ingest-local-drive")
    response = client.post(
        "/jobs/search",
        json={
            "job_title": "AI Engineer",
            "job_description": "Build AI systems.",
            "required_skills": ["Python", "LLM", "LangChain"],
            "nice_to_have_skills": ["Docker"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["matched_count"] == 2
    results = body["results"]
    assert results[0]["file_name"] == "strong-ai-engineer.txt"
    assert results[0]["required_skill_score"] > results[1]["required_skill_score"]


def test_search_does_not_call_parser_during_search(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    monkeypatch.setattr(
        local_resume_batch_processor,
        "_storage_provider",
        LocalFolderResumeStorageProvider(tmp_path),
    )
    monkeypatch.setattr(
        local_resume_batch_processor,
        "_candidate_profile_service",
        CandidateProfileService(
            primary_parser=RuleBasedResumeParserProvider(),
            fallback_parser=RuleBasedResumeParserProvider(),
        ),
    )
    (tmp_path / "ai-engineer.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    client = TestClient(create_app())
    client.post("/resumes/ingest-local-drive")

    class ParserThatShouldNotRun:
        def parse_with_metadata(self, resume_text: str):
            raise AssertionError("Parser should not run during JD search.")

    monkeypatch.setattr(
        local_resume_batch_processor,
        "_candidate_profile_service",
        ParserThatShouldNotRun(),
    )
    response = client.post(
        "/jobs/search",
        json={
            "job_title": "AI Engineer",
            "job_description": "Build AI systems.",
            "required_skills": ["Python"],
            "nice_to_have_skills": [],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["matched_count"] == 1
    assert body["results"][0]["file_name"] == "ai-engineer.txt"


def test_search_keeps_title_matches_and_marks_experience_failures_with_seeded_profiles() -> None:
    resume_repository.clear()
    resume_repository.save(_parsed_record("senior", "senior.txt", 6))
    resume_repository.save(_parsed_record("mid", "mid.txt", 4))
    resume_repository.save(_parsed_record("unknown", "unknown.txt", None))
    client = TestClient(create_app())

    response = client.post(
        "/jobs/search",
        json={
            "job_title": "AI Engineer",
            "job_description": "AI role",
            "required_skills": ["Python"],
            "nice_to_have_skills": [],
            "min_years_experience": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_candidates_considered"] == 3
    assert body["excluded_by_title_count"] == 0
    assert body["excluded_by_experience_count"] == 2
    assert body["matched_count"] == 3
    assert [result["file_name"] for result in body["results"]] == [
        "senior.txt",
        "mid.txt",
        "unknown.txt",
    ]
    assert body["results"][0]["shortlist_decision"] == "shortlist"
    assert body["results"][1]["shortlist_decision"] == "not_recommended"
    assert body["results"][1]["experience_passed"] is False
    assert body["results"][2]["shortlist_decision"] == "review"
    assert body["results"][2]["experience_passed"] is None
    assert "Experience requirement met: 6 years >= 5 years" in body["results"][0]["match_reason"]


def test_search_data_scientist_all_results_include_below_experience_candidate() -> None:
    resume_repository.clear()
    now = datetime.now(UTC)
    for resume_id, file_name, title, years in [
        ("jillani", "Jillani.pdf", "Senior Data Scientist", 5.4),
        ("bhavesh", "Bhavesh.pdf", "Data Scientist", 4.5),
        ("ai", "AI.pdf", "AI Engineer", 8),
    ]:
        resume_repository.save(
            ResumeRecord(
                resume_id=resume_id,
                file_name=file_name,
                source_path=f"/fake/{file_name}",
                file_type="application/pdf",
                file_hash=resume_id,
                last_modified=now,
                extraction_status="extracted",
                parsing_status="parsed",
                parser_used="ollama",
                parsing_error=None,
                ollama_error=None,
                ollama_raw_response_preview=None,
                ollama_model="llama3.1:8b",
                extracted_text=f"{title}\nPython SQL Machine Learning",
                parsed_at=now,
                ingested_at=now,
                candidate_profile=CandidateProfile(
                    candidate_name=file_name,
                    email=f"{resume_id}@example.com",
                    phone=None,
                    current_title=title,
                    skills=["Python", "SQL", "Machine Learning"],
                    total_experience_years=years,
                    companies=[],
                    education=[],
                    resume_summary="",
                    confidence_score=0.9,
                    parsing_status="parsed",
                    parser_used="ollama",
                ),
            )
        )
    client = TestClient(create_app())

    response = client.post(
        "/jobs/search",
        json={
            "job_title": "Data Scientist",
            "job_description": "Data role",
            "required_skills": ["Python", "SQL", "Machine Learning"],
            "nice_to_have_skills": [],
            "min_years_experience": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["excluded_by_title_count"] == 1
    assert body["excluded_by_experience_count"] == 1
    assert body["matched_count"] == 2
    assert [result["file_name"] for result in body["results"]] == [
        "Jillani.pdf",
        "Bhavesh.pdf",
    ]
    assert body["results"][0]["shortlist_decision"] == "shortlist"
    assert body["results"][1]["shortlist_decision"] == "not_recommended"


def test_search_does_not_trigger_batch_processor(monkeypatch) -> None:
    resume_repository.clear()
    resume_repository.save(_parsed_record("senior", "senior.txt", 6))

    def fail_if_called(force: bool = False):
        raise AssertionError("Search must not trigger batch processing.")

    monkeypatch.setattr(
        batch_processing_service,
        "run_local_drive_batch",
        fail_if_called,
    )
    monkeypatch.setattr(
        batch_processing_service,
        "run_batch",
        fail_if_called,
    )
    client = TestClient(create_app())

    response = client.post(
        "/jobs/search",
        json={
            "job_title": "AI Engineer",
            "job_description": "AI role",
            "required_skills": ["Python"],
            "nice_to_have_skills": [],
            "min_years_experience": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["matched_count"] == 1

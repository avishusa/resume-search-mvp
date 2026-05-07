from fastapi.testclient import TestClient

from app.container import resume_batch_processor, resume_repository
from app.main import create_app
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.services.candidate_profile_service import CandidateProfileService


def test_search_jd_returns_only_strict_title_matched_resumes(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    monkeypatch.setattr(resume_batch_processor, "_local_drive_folder", tmp_path)
    monkeypatch.setattr(
        resume_batch_processor,
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
    results = search_response.json()["results"]
    assert [result["file_name"] for result in results] == ["ai-engineer.txt"]


def test_search_ranks_candidates_with_more_required_skills_higher(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    monkeypatch.setattr(resume_batch_processor, "_local_drive_folder", tmp_path)
    monkeypatch.setattr(
        resume_batch_processor,
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
    results = response.json()["results"]
    assert results[0]["file_name"] == "strong-ai-engineer.txt"
    assert results[0]["required_skill_score"] > results[1]["required_skill_score"]


def test_search_does_not_call_parser_during_search(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    monkeypatch.setattr(resume_batch_processor, "_local_drive_folder", tmp_path)
    monkeypatch.setattr(
        resume_batch_processor,
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
        resume_batch_processor,
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
    assert response.json()["results"][0]["file_name"] == "ai-engineer.txt"

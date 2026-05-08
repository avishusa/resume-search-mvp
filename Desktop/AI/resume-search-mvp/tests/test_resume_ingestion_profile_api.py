import json

from fastapi.testclient import TestClient

from app.container import resume_batch_processor, resume_repository
from app.main import create_app
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.services.candidate_profile_service import CandidateProfileService
from app.storage.local_folder import LocalFolderResumeStorageProvider


class FakeOllamaResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "response": json.dumps(
                {
                    "candidate_name": "Jane Candidate",
                    "email": "jane@example.com",
                    "phone": "312-555-1212",
                    "current_title": "AI Engineer",
                    "skills": ["Python", "FastAPI"],
                    "total_experience_years": 4,
                    "companies": ["Acme"],
                    "education": ["BS Computer Science"],
                    "resume_summary": "AI Engineer with Python and FastAPI experience.",
                    "confidence_score": 0.88,
                }
            )
        }


class FakeOllamaClient:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def post(self, url: str, json: dict) -> FakeOllamaResponse:
        return FakeOllamaResponse()


def test_ingest_txt_resume_and_list_parsed_candidate_profile(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    monkeypatch.setattr(
        resume_batch_processor,
        "_storage_provider",
        LocalFolderResumeStorageProvider(tmp_path),
    )
    monkeypatch.setattr(
        "app.parsing.ollama.httpx.Client",
        lambda timeout: FakeOllamaClient(),
    )
    (tmp_path / "jane-candidate.txt").write_text(
        "AI Engineer\njane@example.com\nPython FastAPI",
        encoding="utf-8",
    )
    client = TestClient(create_app())

    ingest_response = client.post("/resumes/ingest-local-drive")
    list_response = client.get("/resumes")

    assert ingest_response.status_code == 200
    assert list_response.status_code == 200
    resumes = list_response.json()
    assert resumes[0]["candidate_name"] == "Jane Candidate"
    assert resumes[0]["email"] == "jane@example.com"
    assert resumes[0]["current_title"] == "AI Engineer"
    assert resumes[0]["skills"] == ["Python", "FastAPI"]
    assert resumes[0]["parsing_status"] == "parsed"
    assert resumes[0]["parser_used"] == "ollama"


def test_ingest_local_drive_force_query_reprocesses_existing_resume(
    tmp_path,
    monkeypatch,
) -> None:
    resume_repository.clear()
    monkeypatch.setattr(
        resume_batch_processor,
        "_storage_provider",
        LocalFolderResumeStorageProvider(tmp_path),
    )
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

    first_response = client.post("/resumes/ingest-local-drive")
    second_response = client.post("/resumes/ingest-local-drive?force=true")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["ingested_count"] == 1
    assert second_response.json()["updated_count"] == 1
    assert second_response.json()["skipped_count"] == 0

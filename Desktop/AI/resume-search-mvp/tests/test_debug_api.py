import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.container import debug_service
from app.main import create_app
from app.storage.base import ResumeFileReference


class FakeOllamaResponse:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {"response": self._response_text}


class FakeOllamaClient:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def post(self, url: str, json: dict) -> FakeOllamaResponse:
        if json["prompt"] == 'Return only JSON: {"status":"ok"}':
            return FakeOllamaResponse('{"status":"ok"}')

        return FakeOllamaResponse(
            json_module.dumps(
                {
                    "candidate_name": "Bhavesh Wadhwani",
                    "email": "test@example.com",
                    "phone": None,
                    "current_title": "DATA SCIENTIST",
                    "skills": ["Python", "SQL"],
                    "total_experience_years": None,
                    "companies": [],
                    "education": [],
                    "resume_summary": "Data scientist with Python and SQL.",
                    "confidence_score": 0.82,
                }
            )
        )


json_module = json


def test_debug_ollama_returns_config_and_success_when_mocked(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.debug_service.httpx.Client",
        lambda timeout: FakeOllamaClient(),
    )
    client = TestClient(create_app())

    response = client.get("/debug/ollama")

    assert response.status_code == 200
    body = response.json()
    assert body["resume_parser_provider"] == "ollama"
    assert body["ollama_base_url"] == "http://localhost:11434"
    assert body["ollama_model"] == "llama3.1:8b"
    assert isinstance(body["ollama_timeout_seconds"], int)
    assert isinstance(body["ollama_max_resume_chars"], int)
    assert body["ollama_reachable"] is True
    assert body["test_generation_success"] is True
    assert body["error"] is None


def test_debug_parse_resume_text_uses_ollama_when_mocked_successfully(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.parsing.ollama.httpx.Client",
        lambda timeout: FakeOllamaClient(),
    )
    client = TestClient(create_app())

    response = client.post(
        "/debug/parse-resume-text",
        json={
            "text": (
                "Bhavesh Wadhwani\nDATA SCIENTIST\n"
                "Email: test@example.com\nSkills: Python, SQL"
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["parser_used"] == "ollama"
    assert body["profile"]["candidate_name"] == "Bhavesh Wadhwani"
    assert body["profile"]["email"] == "test@example.com"
    assert body["profile"]["skills"] == ["Python", "SQL"]
    assert body["parsing_error"] is None
    assert body["ollama_error"] is None
    assert body["ollama_raw_response_preview"]


def test_debug_storage_provider_returns_local_status(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(debug_service._settings, "local_drive_resume_dir", str(tmp_path))
    (tmp_path / "resume.txt").write_text("AI Engineer", encoding="utf-8")
    client = TestClient(create_app())

    response = client.get("/debug/storage-provider")

    assert response.status_code == 200
    body = response.json()
    assert body["configured_providers"] == ["local"]
    assert body["providers"][0]["provider_name"] == "local"
    assert body["providers"][0]["exists"] is True
    assert body["providers"][0]["recursive"] is True
    assert body["providers"][0]["supported_file_count"] == 1


class FakeGoogleDebugProvider:
    provider_name = "google_drive"
    last_folders_seen = 3
    last_errors: list[str] = []

    def list_resume_files(self) -> list[ResumeFileReference]:
        return [
            ResumeFileReference(
                source_id="drive-file-1",
                source_path="drive://Recruiting Resumes/Data Science/resume.pdf",
                file_name="resume.pdf",
                file_type="application/pdf",
                last_modified=datetime.now(UTC),
                size_bytes=123,
                provider_name=self.provider_name,
                folder_path="Recruiting Resumes/Data Science",
            )
        ]


def test_debug_storage_provider_returns_google_recursive_status(
    tmp_path,
    monkeypatch,
) -> None:
    service_account_file = tmp_path / "service-account.json"
    service_account_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "app.services.debug_service.create_google_drive_resume_storage_provider",
        lambda settings: FakeGoogleDebugProvider(),
    )
    monkeypatch.setattr(debug_service._settings, "resume_storage_providers", "google_drive")
    monkeypatch.setattr(debug_service._settings, "google_drive_folder_id", "folder-id")
    monkeypatch.setattr(
        debug_service._settings,
        "google_service_account_file",
        str(service_account_file),
    )
    client = TestClient(create_app())

    response = client.get("/debug/storage-provider")

    assert response.status_code == 200
    body = response.json()
    provider_status = body["providers"][0]
    assert body["configured_providers"] == ["google_drive"]
    assert provider_status["provider_name"] == "google_drive"
    assert provider_status["recursive_enabled"] is True
    assert provider_status["max_depth"] == 10
    assert provider_status["max_files"] == 1000
    assert provider_status["can_list_files"] is True
    assert provider_status["supported_file_count"] == 1
    assert provider_status["folders_seen"] == 3

from fastapi.testclient import TestClient

from app.container import (
    batch_run_repository,
    local_resume_batch_processor,
    resume_batch_processor,
    resume_repository,
)
from app.main import create_app
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.services.candidate_profile_service import CandidateProfileService
from app.storage.local_folder import LocalFolderResumeStorageProvider


def test_batch_run_local_drive_endpoint_records_run(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    batch_run_repository.clear()
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
    (tmp_path / "resume.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    client = TestClient(create_app())

    run_response = client.post("/batch/run-local-drive")
    list_response = client.get("/batch/runs")
    detail_response = client.get(f"/batch/runs/{run_response.json()['batch_id']}")

    assert run_response.status_code == 200
    assert run_response.json()["status"] == "completed"
    assert run_response.json()["ingested_count"] == 1
    assert list_response.status_code == 200
    assert len(list_response.json()["runs"]) >= 1
    assert detail_response.status_code == 200
    assert detail_response.json()["batch_id"] == run_response.json()["batch_id"]


def test_batch_run_endpoint_uses_configured_provider(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    batch_run_repository.clear()
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
    (tmp_path / "configured-provider-resume.txt").write_text(
        "AI Engineer\nPython",
        encoding="utf-8",
    )
    client = TestClient(create_app())

    response = client.post("/batch/run")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["ingested_count"] == 1
    assert resume_repository.list_all()[0].file_name == "configured-provider-resume.txt"


def test_active_batch_status_returns_false_when_no_batch_is_running() -> None:
    batch_run_repository.clear()
    client = TestClient(create_app())

    response = client.get("/batch/runs/active")

    assert response.status_code == 200
    assert response.json() == {
        "is_running": False,
        "batch_id": None,
        "started_at": None,
        "status": None,
    }


def test_active_batch_status_returns_running_batch() -> None:
    batch_run_repository.clear()
    client = TestClient(create_app())
    batch_run = batch_run_repository.create_running()

    response = client.get("/batch/runs/active")

    assert response.status_code == 200
    body = response.json()
    assert body["is_running"] is True
    assert body["batch_id"] == batch_run.batch_id
    assert body["started_at"] == batch_run.started_at.isoformat()
    assert body["status"] == "running"


def test_second_batch_request_while_running_returns_409(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    batch_run_repository.clear()
    monkeypatch.setattr(
        local_resume_batch_processor,
        "_storage_provider",
        LocalFolderResumeStorageProvider(tmp_path),
    )
    client = TestClient(create_app())
    batch_run = batch_run_repository.create_running()

    response = client.post("/batch/run-local-drive")

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "message": "A batch run is already in progress.",
        "batch_id": batch_run.batch_id,
        "started_at": batch_run.started_at.isoformat(),
    }


def test_completed_batch_clears_active_status(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    batch_run_repository.clear()
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
    (tmp_path / "resume.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    client = TestClient(create_app())

    run_response = client.post("/batch/run-local-drive")
    active_response = client.get("/batch/runs/active")

    assert run_response.status_code == 200
    assert run_response.json()["status"] == "completed"
    assert active_response.status_code == 200
    assert active_response.json()["is_running"] is False

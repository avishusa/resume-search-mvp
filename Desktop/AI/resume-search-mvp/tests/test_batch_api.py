from fastapi.testclient import TestClient

from app.container import batch_run_repository, resume_batch_processor, resume_repository
from app.main import create_app
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.services.candidate_profile_service import CandidateProfileService


def test_batch_run_local_drive_endpoint_records_run(tmp_path, monkeypatch) -> None:
    resume_repository.clear()
    batch_run_repository.clear()
    monkeypatch.setattr(resume_batch_processor, "_local_drive_folder", tmp_path)
    monkeypatch.setattr(
        resume_batch_processor,
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

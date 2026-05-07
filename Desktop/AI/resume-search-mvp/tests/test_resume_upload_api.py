from fastapi.testclient import TestClient

from app.container import resume_ingestion_service, resume_repository
from app.main import create_app


def test_upload_txt_resume_returns_extracted_preview(monkeypatch) -> None:
    resume_repository.clear()
    monkeypatch.setattr(resume_ingestion_service, "_candidate_profile_service", None)
    client = TestClient(create_app())

    response = client.post(
        "/resumes/upload",
        files={
            "file": (
                "candidate.txt",
                b"Senior recruiter resume\nBuilt sourcing pipelines",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["resume_id"]
    assert body["file_name"] == "candidate.txt"
    assert body["mime_type"] == "text/plain"
    assert body["extraction_status"] == "extracted"
    assert body["extracted_text_preview"] == (
        "Senior recruiter resume\nBuilt sourcing pipelines"
    )


def test_upload_rejects_unsupported_file_type(monkeypatch) -> None:
    resume_repository.clear()
    monkeypatch.setattr(resume_ingestion_service, "_candidate_profile_service", None)
    client = TestClient(create_app())

    response = client.post(
        "/resumes/upload",
        files={"file": ("candidate.png", b"not a resume", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF, DOCX, and TXT files are supported."

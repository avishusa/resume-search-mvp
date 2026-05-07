import pymupdf
from docx import Document

from app.repositories.resume_repository import InMemoryResumeRepository
from app.services.resume_ingestion_service import ResumeIngestionService


def _write_pdf(path, text: str) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    path.write_bytes(document.tobytes())
    document.close()


def _write_docx(path, paragraphs: list[str]) -> None:
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    document.save(path)


def test_ingest_local_drive_folder_with_fake_txt_resumes(tmp_path) -> None:
    (tmp_path / "ai-engineer.txt").write_text(
        "AI Engineer\nPython LLM LangChain",
        encoding="utf-8",
    )
    (tmp_path / "notes.png").write_bytes(b"unsupported")
    repository = InMemoryResumeRepository()
    service = ResumeIngestionService(repository=repository, local_drive_folder=tmp_path)

    response = service.ingest_local_drive()

    assert response.total_files_seen == 2
    assert response.ingested_count == 1
    assert response.skipped_count == 1
    assert response.failed_count == 0
    assert response.resumes[0].file_name == "ai-engineer.txt"
    assert repository.list_all()[0].extracted_text == "AI Engineer\nPython LLM LangChain"


def test_ingest_local_drive_skips_duplicate_source_paths(tmp_path) -> None:
    (tmp_path / "ai-engineer.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    repository = InMemoryResumeRepository()
    service = ResumeIngestionService(repository=repository, local_drive_folder=tmp_path)

    first_response = service.ingest_local_drive()
    second_response = service.ingest_local_drive()

    assert first_response.ingested_count == 1
    assert second_response.ingested_count == 0
    assert second_response.skipped_count == 1
    assert len(repository.list_all()) == 1


def test_ingest_local_drive_pdf_does_not_return_not_implemented(tmp_path) -> None:
    _write_pdf(tmp_path / "ai-engineer.pdf", "AI Engineer\nPython")
    repository = InMemoryResumeRepository()
    service = ResumeIngestionService(repository=repository, local_drive_folder=tmp_path)

    response = service.ingest_local_drive()

    assert response.ingested_count == 1
    assert response.resumes[0].extraction_status == "extracted"
    assert response.resumes[0].extraction_status != "not_implemented"
    assert "AI Engineer" in response.resumes[0].extracted_text_preview


def test_ingest_local_drive_txt_and_docx_do_not_return_not_implemented(tmp_path) -> None:
    (tmp_path / "ai-engineer.txt").write_text("AI Engineer\nPython", encoding="utf-8")
    _write_docx(tmp_path / "software-engineer.docx", ["Software Engineer", "Docker"])
    repository = InMemoryResumeRepository()
    service = ResumeIngestionService(repository=repository, local_drive_folder=tmp_path)

    response = service.ingest_local_drive()

    statuses = {resume.file_name: resume.extraction_status for resume in response.resumes}
    assert response.ingested_count == 2
    assert statuses["ai-engineer.txt"] == "extracted"
    assert statuses["software-engineer.docx"] == "extracted"
    assert "not_implemented" not in statuses.values()

from datetime import UTC, datetime

import pytest

from app.storage.base import ResumeFileReference
from app.storage.google_drive import GoogleDriveResumeStorageProvider
from app.storage.local_folder import LocalFolderResumeStorageProvider


def test_local_folder_provider_lists_only_supported_resume_files(tmp_path) -> None:
    (tmp_path / "resume.txt").write_text("AI Engineer", encoding="utf-8")
    (tmp_path / "resume.pdf").write_bytes(b"%PDF")
    (tmp_path / "resume.docx").write_bytes(b"docx")
    (tmp_path / "notes.png").write_bytes(b"unsupported")
    provider = LocalFolderResumeStorageProvider(tmp_path)

    files = provider.list_resume_files()

    assert [file.file_name for file in files] == [
        "resume.docx",
        "resume.pdf",
        "resume.txt",
    ]


def test_local_folder_provider_returns_metadata(tmp_path) -> None:
    resume_path = tmp_path / "resume.txt"
    resume_path.write_text("AI Engineer", encoding="utf-8")
    provider = LocalFolderResumeStorageProvider(tmp_path)

    file_reference = provider.list_resume_files()[0]

    assert file_reference.source_id == str(resume_path.resolve())
    assert file_reference.source_path == str(resume_path.resolve())
    assert file_reference.file_name == "resume.txt"
    assert file_reference.file_type == "text/plain"
    assert file_reference.provider_name == "local"
    assert file_reference.size_bytes == len("AI Engineer")
    assert file_reference.last_modified is not None


def test_local_folder_provider_reads_file_bytes(tmp_path) -> None:
    (tmp_path / "resume.txt").write_text("AI Engineer", encoding="utf-8")
    provider = LocalFolderResumeStorageProvider(tmp_path)
    file_reference = provider.list_resume_files()[0]

    assert provider.read_file(file_reference) == b"AI Engineer"


def test_google_drive_provider_is_placeholder() -> None:
    provider = GoogleDriveResumeStorageProvider()

    with pytest.raises(NotImplementedError):
        provider.list_resume_files()

    with pytest.raises(NotImplementedError):
        provider.read_file(
            ResumeFileReference(
                source_id="id",
                source_path="drive://id",
                file_name="resume.pdf",
                file_type="application/pdf",
                last_modified=datetime.now(UTC),
                size_bytes=10,
                provider_name="google_drive",
            )
        )

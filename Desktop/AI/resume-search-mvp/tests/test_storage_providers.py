from datetime import UTC, datetime

import pytest

from app.storage.base import ResumeFileReference
from app.storage.factory import (
    StorageProviderConfigurationError,
    create_resume_storage_provider,
    get_storage_providers,
)
from app.storage.google_drive import GoogleDriveResumeStorageProvider
from app.storage.local_folder import LocalFolderResumeStorageProvider
from app.config import Settings


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


class FakeGoogleRequest:
    def __init__(self, response) -> None:
        self._response = response

    def execute(self):
        return self._response


class FakeGoogleFilesResource:
    def __init__(self) -> None:
        self.download_file_id = None
        self.list_kwargs = None

    def list(self, **kwargs):
        self.list_kwargs = kwargs
        return FakeGoogleRequest(
            {
                "files": [
                    {
                        "id": "pdf-1",
                        "name": "resume.pdf",
                        "mimeType": "application/pdf",
                        "modifiedTime": "2026-05-08T10:30:00Z",
                        "size": "1234",
                    },
                    {
                        "id": "docx-1",
                        "name": "resume.docx",
                        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "modifiedTime": "2026-05-08T11:00:00Z",
                        "size": "4567",
                    },
                    {
                        "id": "folder-1",
                        "name": "Nested Folder",
                        "mimeType": "application/vnd.google-apps.folder",
                    },
                    {
                        "id": "image-1",
                        "name": "photo.png",
                        "mimeType": "image/png",
                    },
                ]
            }
        )

    def get_media(self, **kwargs):
        self.download_file_id = kwargs["fileId"]
        return FakeGoogleRequest(b"downloaded resume bytes")


class FakeGoogleDriveService:
    def __init__(self) -> None:
        self.files_resource = FakeGoogleFilesResource()

    def files(self):
        return self.files_resource


def test_provider_factory_returns_local_provider_by_default(monkeypatch) -> None:
    monkeypatch.delenv("RESUME_STORAGE_PROVIDER", raising=False)
    monkeypatch.delenv("RESUME_STORAGE_PROVIDERS", raising=False)

    provider = create_resume_storage_provider(Settings(_env_file=None))

    assert isinstance(provider, LocalFolderResumeStorageProvider)


def test_provider_factory_returns_local_provider_list_by_default(monkeypatch) -> None:
    monkeypatch.delenv("RESUME_STORAGE_PROVIDER", raising=False)
    monkeypatch.delenv("RESUME_STORAGE_PROVIDERS", raising=False)

    providers = get_storage_providers(Settings(_env_file=None))

    assert len(providers) == 1
    assert isinstance(providers[0], LocalFolderResumeStorageProvider)


def test_provider_factory_returns_multiple_configured_providers(monkeypatch) -> None:
    monkeypatch.setenv("RESUME_STORAGE_PROVIDERS", "local,google_drive")
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")

    providers = get_storage_providers(Settings(_env_file=None))

    assert [provider.provider_name for provider in providers] == [
        "local",
        "google_drive",
    ]


def test_provider_factory_unknown_provider_raises_clear_error(monkeypatch) -> None:
    monkeypatch.setenv("RESUME_STORAGE_PROVIDERS", "local,unknown")

    with pytest.raises(StorageProviderConfigurationError) as error:
        get_storage_providers(Settings(_env_file=None))

    assert "Unsupported resume storage provider: unknown" in str(error.value)


def test_provider_factory_returns_google_provider_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("RESUME_STORAGE_PROVIDER", "google_drive")
    monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "folder-id")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")

    provider = create_resume_storage_provider(Settings(_env_file=None))

    assert isinstance(provider, GoogleDriveResumeStorageProvider)


def test_provider_factory_missing_google_config_raises_clear_error(monkeypatch) -> None:
    monkeypatch.setenv("RESUME_STORAGE_PROVIDER", "google_drive")
    monkeypatch.delenv("GOOGLE_DRIVE_FOLDER_ID", raising=False)
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)

    with pytest.raises(StorageProviderConfigurationError) as error:
        create_resume_storage_provider(Settings(_env_file=None))

    assert "GOOGLE_DRIVE_FOLDER_ID is required" in str(error.value)


def test_google_drive_provider_filters_and_maps_metadata() -> None:
    service = FakeGoogleDriveService()
    provider = GoogleDriveResumeStorageProvider(
        folder_id="folder-id",
        service_account_file="service-account.json",
        allowed_mime_types=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
        ],
        drive_service=service,
    )

    files = provider.list_resume_files()

    assert [file.file_name for file in files] == ["resume.pdf", "resume.docx"]
    assert files[0].source_id == "pdf-1"
    assert files[0].source_path == "google_drive://pdf-1"
    assert files[0].file_type == "application/pdf"
    assert files[0].provider_name == "google_drive"
    assert files[0].size_bytes == 1234
    assert files[0].last_modified.isoformat() == "2026-05-08T10:30:00+00:00"
    assert service.files_resource.list_kwargs["q"] == (
        "'folder-id' in parents and trashed = false"
    )


def test_google_drive_provider_downloads_by_file_id() -> None:
    service = FakeGoogleDriveService()
    provider = GoogleDriveResumeStorageProvider(
        folder_id="folder-id",
        service_account_file="service-account.json",
        allowed_mime_types=["application/pdf"],
        drive_service=service,
    )

    file_bytes = provider.read_file(
        ResumeFileReference(
            source_id="pdf-1",
            source_path="google_drive://pdf-1",
            file_name="resume.pdf",
            file_type="application/pdf",
            last_modified=datetime.now(UTC),
            size_bytes=10,
            provider_name="google_drive",
        )
    )

    assert file_bytes == b"downloaded resume bytes"
    assert service.files_resource.download_file_id == "pdf-1"

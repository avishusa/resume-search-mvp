from pathlib import Path

from app.config import Settings
from app.storage.base import ResumeStorageProvider
from app.storage.google_drive import GoogleDriveResumeStorageProvider
from app.storage.local_folder import LocalFolderResumeStorageProvider


class StorageProviderConfigurationError(ValueError):
    """Raised when the configured resume storage provider cannot be created."""


def create_resume_storage_provider(settings: Settings) -> ResumeStorageProvider:
    provider_name = settings.resume_storage_provider.strip().lower()

    if provider_name == "local":
        return create_local_resume_storage_provider(settings)

    if provider_name == "google_drive":
        return create_google_drive_resume_storage_provider(settings)

    raise StorageProviderConfigurationError(
        f"Unsupported RESUME_STORAGE_PROVIDER: {settings.resume_storage_provider}"
    )


def create_local_resume_storage_provider(settings: Settings) -> ResumeStorageProvider:
    return LocalFolderResumeStorageProvider(Path(settings.local_drive_resume_dir))


def create_google_drive_resume_storage_provider(
    settings: Settings,
) -> ResumeStorageProvider:
    if not settings.google_drive_folder_id.strip():
        raise StorageProviderConfigurationError(
            "GOOGLE_DRIVE_FOLDER_ID is required when RESUME_STORAGE_PROVIDER=google_drive."
        )
    if not settings.google_service_account_file.strip():
        raise StorageProviderConfigurationError(
            "GOOGLE_SERVICE_ACCOUNT_FILE is required when RESUME_STORAGE_PROVIDER=google_drive."
        )

    allowed_mime_types = [
        mime_type.strip()
        for mime_type in settings.google_drive_allowed_mime_types.split(",")
        if mime_type.strip()
    ]
    if not allowed_mime_types:
        raise StorageProviderConfigurationError(
            "GOOGLE_DRIVE_ALLOWED_MIME_TYPES must include at least one MIME type."
        )

    return GoogleDriveResumeStorageProvider(
        folder_id=settings.google_drive_folder_id,
        service_account_file=settings.google_service_account_file,
        allowed_mime_types=allowed_mime_types,
    )

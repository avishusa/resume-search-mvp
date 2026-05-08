from app.storage.base import ResumeFileReference


class GoogleDriveResumeStorageProvider:
    """Placeholder for future Google Drive integration.

    A production implementation will authenticate with Google Drive, list files
    from a configured Drive folder, download file bytes, and provide metadata
    using ResumeFileReference.
    """

    provider_name = "google_drive"

    def list_resume_files(self) -> list[ResumeFileReference]:
        raise NotImplementedError("Google Drive storage provider is not implemented yet.")

    def read_file(self, file_reference: ResumeFileReference) -> bytes:
        raise NotImplementedError("Google Drive storage provider is not implemented yet.")

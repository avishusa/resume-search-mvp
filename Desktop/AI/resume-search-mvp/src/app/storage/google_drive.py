from datetime import datetime

from app.storage.base import ResumeFileReference


GOOGLE_DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
GOOGLE_DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"


class GoogleDriveStorageError(RuntimeError):
    """Raised when Google Drive cannot list or download resume files."""


class GoogleDriveResumeStorageProvider:
    """Google Drive-backed resume storage provider.

    This provider authenticates with a Google service account, lists supported
    resume files from one configured Drive folder, and downloads file bytes for
    batch ingestion. It intentionally stays behind ResumeStorageProvider so the
    batch processor does not need Google-specific code.
    """

    provider_name = "google_drive"

    def __init__(
        self,
        folder_id: str,
        service_account_file: str,
        allowed_mime_types: list[str],
        drive_service=None,
    ) -> None:
        self._folder_id = folder_id
        self._service_account_file = service_account_file
        self._allowed_mime_types = set(allowed_mime_types)
        self._drive_service = drive_service

    def list_resume_files(self) -> list[ResumeFileReference]:
        service = self._get_drive_service()
        references: list[ResumeFileReference] = []
        page_token: str | None = None

        try:
            while True:
                response = (
                    service.files()
                    .list(
                        q=f"'{self._folder_id}' in parents and trashed = false",
                        fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                        pageSize=1000,
                        pageToken=page_token,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                    )
                    .execute()
                )

                for file_metadata in response.get("files", []):
                    reference = self._to_file_reference(file_metadata)
                    if reference is not None:
                        references.append(reference)

                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        except Exception as exception:
            raise GoogleDriveStorageError(
                f"Google Drive file listing failed: {exception}"
            ) from exception

        return references

    def read_file(self, file_reference: ResumeFileReference) -> bytes:
        service = self._get_drive_service()
        try:
            return (
                service.files()
                .get_media(
                    fileId=file_reference.source_id,
                    supportsAllDrives=True,
                )
                .execute()
            )
        except Exception as exception:
            raise GoogleDriveStorageError(
                f"Google Drive download failed for {file_reference.source_id}: {exception}"
            ) from exception

    def _get_drive_service(self):
        if self._drive_service is None:
            self._drive_service = self._build_drive_service()
        return self._drive_service

    def _build_drive_service(self):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            credentials = service_account.Credentials.from_service_account_file(
                self._service_account_file,
                scopes=[GOOGLE_DRIVE_READONLY_SCOPE],
            )
            return build(
                "drive",
                "v3",
                credentials=credentials,
                cache_discovery=False,
            )
        except Exception as exception:
            raise GoogleDriveStorageError(
                f"Google Drive authentication failed: {exception}"
            ) from exception

    def _to_file_reference(
        self,
        file_metadata: dict,
    ) -> ResumeFileReference | None:
        mime_type = file_metadata.get("mimeType")
        if mime_type == GOOGLE_DRIVE_FOLDER_MIME_TYPE:
            return None
        if mime_type not in self._allowed_mime_types:
            return None

        file_id = file_metadata["id"]
        return ResumeFileReference(
            source_id=file_id,
            source_path=f"google_drive://{file_id}",
            file_name=file_metadata.get("name", file_id),
            file_type=mime_type,
            last_modified=self._parse_modified_time(file_metadata.get("modifiedTime")),
            size_bytes=self._parse_size(file_metadata.get("size")),
            provider_name=self.provider_name,
        )

    def _parse_modified_time(self, modified_time: str | None) -> datetime | None:
        if not modified_time:
            return None
        return datetime.fromisoformat(modified_time.replace("Z", "+00:00"))

    def _parse_size(self, size: str | int | None) -> int | None:
        if size is None:
            return None
        return int(size)

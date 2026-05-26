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
        recursive: bool = True,
        max_depth: int = 10,
        max_files: int = 1000,
        drive_service=None,
    ) -> None:
        self._folder_id = folder_id
        self._service_account_file = service_account_file
        self._allowed_mime_types = set(allowed_mime_types)
        self._recursive = recursive
        self._max_depth = max(0, max_depth)
        self._max_files = max(1, max_files)
        self._drive_service = drive_service
        self.last_folders_seen = 0
        self.last_errors: list[str] = []

    def list_resume_files(self) -> list[ResumeFileReference]:
        service = self._get_drive_service()
        references: list[ResumeFileReference] = []
        visited_folder_ids: set[str] = set()
        self.last_folders_seen = 0
        self.last_errors = []

        root_folder_path = self._get_folder_name(service, self._folder_id)

        try:
            self._scan_folder(
                service=service,
                folder_id=self._folder_id,
                folder_path=root_folder_path,
                depth=0,
                visited_folder_ids=visited_folder_ids,
                references=references,
            )
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

    def _scan_folder(
        self,
        service,
        folder_id: str,
        folder_path: str,
        depth: int,
        visited_folder_ids: set[str],
        references: list[ResumeFileReference],
    ) -> bool:
        if folder_id in visited_folder_ids:
            return True
        if depth > self._max_depth:
            return True

        visited_folder_ids.add(folder_id)
        self.last_folders_seen += 1
        page_token: str | None = None

        while True:
            try:
                response = self._list_folder_children(service, folder_id, page_token)
            except Exception as exception:
                message = (
                    f"Google Drive file listing failed for folder "
                    f"{folder_path} ({folder_id}): {exception}"
                )
                if depth == 0:
                    raise GoogleDriveStorageError(message) from exception
                self.last_errors.append(message)
                return True

            for file_metadata in response.get("files", []):
                if len(references) >= self._max_files:
                    return False

                mime_type = file_metadata.get("mimeType")
                if mime_type == GOOGLE_DRIVE_FOLDER_MIME_TYPE:
                    if self._recursive and depth < self._max_depth:
                        child_folder_id = file_metadata.get("id")
                        if child_folder_id:
                            child_folder_path = self._join_drive_path(
                                folder_path,
                                file_metadata.get("name", child_folder_id),
                            )
                            should_continue = self._scan_folder(
                                service=service,
                                folder_id=child_folder_id,
                                folder_path=child_folder_path,
                                depth=depth + 1,
                                visited_folder_ids=visited_folder_ids,
                                references=references,
                            )
                            if not should_continue:
                                return False
                    continue

                reference = self._to_file_reference(file_metadata, folder_path)
                if reference is not None:
                    references.append(reference)

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return True

    def _list_folder_children(
        self,
        service,
        folder_id: str,
        page_token: str | None,
    ) -> dict:
        return (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                pageSize=1000,
                pageToken=page_token,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )

    def _to_file_reference(
        self,
        file_metadata: dict,
        folder_path: str | None = None,
    ) -> ResumeFileReference | None:
        mime_type = file_metadata.get("mimeType")
        if mime_type == GOOGLE_DRIVE_FOLDER_MIME_TYPE:
            return None
        if mime_type not in self._allowed_mime_types:
            return None

        file_id = file_metadata["id"]
        file_name = file_metadata.get("name", file_id)
        return ResumeFileReference(
            source_id=file_id,
            source_path=self._build_source_path(folder_path, file_name, file_id),
            file_name=file_name,
            file_type=mime_type,
            last_modified=self._parse_modified_time(file_metadata.get("modifiedTime")),
            size_bytes=self._parse_size(file_metadata.get("size")),
            provider_name=self.provider_name,
            folder_path=folder_path,
        )

    def _get_folder_name(self, service, folder_id: str) -> str:
        try:
            folder_metadata = (
                service.files()
                .get(
                    fileId=folder_id,
                    fields="id, name",
                    supportsAllDrives=True,
                )
                .execute()
            )
            folder_name = folder_metadata.get("name")
            if folder_name:
                return folder_name
        except Exception:
            return folder_id
        return folder_id

    def _build_source_path(
        self,
        folder_path: str | None,
        file_name: str,
        file_id: str,
    ) -> str:
        if folder_path:
            return f"drive://{self._join_drive_path(folder_path, file_name)}"
        return f"drive://{file_id}"

    def _join_drive_path(self, parent_path: str, child_name: str) -> str:
        if not parent_path:
            return child_name
        return f"{parent_path.rstrip('/')}/{child_name.lstrip('/')}"

    def _parse_modified_time(self, modified_time: str | None) -> datetime | None:
        if not modified_time:
            return None
        return datetime.fromisoformat(modified_time.replace("Z", "+00:00"))

    def _parse_size(self, size: str | int | None) -> int | None:
        if size is None:
            return None
        return int(size)

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.storage.base import ResumeFileReference


@dataclass(frozen=True)
class SupportedFileType:
    suffix: str
    mime_type: str


class LocalFolderResumeStorageProvider:
    provider_name = "local"

    def __init__(self, resume_folder: Path | str) -> None:
        self._resume_folder = Path(resume_folder)
        self._supported_file_types = {
            ".pdf": SupportedFileType(".pdf", "application/pdf"),
            ".docx": SupportedFileType(
                ".docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ".txt": SupportedFileType(".txt", "text/plain"),
        }

    def list_resume_files(self) -> list[ResumeFileReference]:
        if not self._resume_folder.exists():
            return []

        references: list[ResumeFileReference] = []
        for path in sorted(self._resume_folder.iterdir()):
            if not path.is_file():
                continue

            file_type = self._supported_file_types.get(path.suffix.lower())
            if file_type is None:
                continue

            stat = path.stat()
            source_path = str(path.resolve())
            references.append(
                ResumeFileReference(
                    source_id=source_path,
                    source_path=source_path,
                    file_name=path.name,
                    file_type=file_type.mime_type,
                    last_modified=datetime.fromtimestamp(stat.st_mtime, UTC),
                    size_bytes=stat.st_size,
                    provider_name=self.provider_name,
                )
            )

        return references

    def read_file(self, file_reference: ResumeFileReference) -> bytes:
        return Path(file_reference.source_path).read_bytes()

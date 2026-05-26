from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ResumeFileReference:
    source_id: str
    source_path: str
    file_name: str
    file_type: str
    last_modified: datetime | None
    size_bytes: int | None
    provider_name: str
    folder_path: str | None = None


class ResumeStorageProvider(Protocol):
    provider_name: str

    def list_resume_files(self) -> list[ResumeFileReference]:
        """Return supported resume files available from this storage provider."""

    def read_file(self, file_reference: ResumeFileReference) -> bytes:
        """Read the full file bytes for a resume reference."""

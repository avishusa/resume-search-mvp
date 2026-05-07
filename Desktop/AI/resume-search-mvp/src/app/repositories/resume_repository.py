from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ResumeRecord:
    resume_id: str
    file_name: str
    source_path: str | None
    mime_type: str
    extracted_text: str
    extraction_status: str
    ingested_at: datetime


class InMemoryResumeRepository:
    def __init__(self) -> None:
        self._records: dict[str, ResumeRecord] = {}
        self._source_path_index: dict[str, str] = {}

    def save(self, record: ResumeRecord) -> ResumeRecord:
        self._records[record.resume_id] = record
        if record.source_path is not None:
            self._source_path_index[record.source_path] = record.resume_id
        return record

    def get(self, resume_id: str) -> ResumeRecord | None:
        return self._records.get(resume_id)

    def get_by_source_path(self, source_path: str) -> ResumeRecord | None:
        resume_id = self._source_path_index.get(source_path)
        if resume_id is None:
            return None
        return self.get(resume_id)

    def list_all(self) -> list[ResumeRecord]:
        return list(self._records.values())

    def clear(self) -> None:
        self._records.clear()
        self._source_path_index.clear()

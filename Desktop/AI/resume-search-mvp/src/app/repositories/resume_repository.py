from dataclasses import dataclass
from datetime import datetime

from app.schemas.candidate import CandidateProfile


@dataclass(frozen=True)
class ResumeRecord:
    resume_id: str
    file_name: str
    source_path: str | None
    file_type: str
    file_hash: str
    last_modified: datetime | None
    extraction_status: str
    parsing_status: str | None
    parser_used: str | None
    parsing_error: str | None
    ollama_error: str | None
    ollama_raw_response_preview: str | None
    ollama_model: str | None
    extracted_text: str
    parsed_at: datetime | None
    ingested_at: datetime
    candidate_profile: CandidateProfile | None = None

    @property
    def mime_type(self) -> str:
        return self.file_type

    @property
    def extracted_text_preview(self) -> str:
        return self.extracted_text[:300]


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

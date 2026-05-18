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
    created_at: datetime | None = None
    updated_at: datetime | None = None
    candidate_profile: CandidateProfile | None = None
    provider_name: str = "local"
    source_id: str | None = None

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
        self._provider_source_index: dict[tuple[str, str], str] = {}

    def save(self, record: ResumeRecord) -> ResumeRecord:
        self._records[record.resume_id] = record
        if record.source_path is not None:
            self._source_path_index[record.source_path] = record.resume_id
        if record.source_id is not None:
            self._provider_source_index[
                (record.provider_name, record.source_id)
            ] = record.resume_id
        return record

    def get(self, resume_id: str) -> ResumeRecord | None:
        return self._records.get(resume_id)

    def get_by_source_path(self, source_path: str) -> ResumeRecord | None:
        resume_id = self._source_path_index.get(source_path)
        if resume_id is None:
            return None
        return self.get(resume_id)

    def get_by_source_path_and_file_hash(
        self,
        source_path: str,
        file_hash: str,
    ) -> ResumeRecord | None:
        record = self.get_by_source_path(source_path)
        if record is None or record.file_hash != file_hash:
            return None
        return record

    def get_by_provider_and_source_id(
        self,
        provider_name: str,
        source_id: str,
    ) -> ResumeRecord | None:
        resume_id = self._provider_source_index.get((provider_name, source_id))
        if resume_id is None:
            return None
        return self.get(resume_id)

    def get_by_provider_source_id_and_file_hash(
        self,
        provider_name: str,
        source_id: str,
        file_hash: str,
    ) -> ResumeRecord | None:
        record = self.get_by_provider_and_source_id(provider_name, source_id)
        if record is None or record.file_hash != file_hash:
            return None
        return record

    def list_all(self) -> list[ResumeRecord]:
        return list(self._records.values())

    def list_searchable(self) -> list[ResumeRecord]:
        return [
            record
            for record in self.list_all()
            if record.extraction_status == "extracted"
            and record.parsing_status in {"parsed", "review_required"}
            and record.candidate_profile is not None
        ]

    def clear(self) -> None:
        self._records.clear()
        self._source_path_index.clear()
        self._provider_source_index.clear()

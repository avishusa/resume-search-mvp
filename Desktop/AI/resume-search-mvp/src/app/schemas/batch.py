from pydantic import BaseModel, Field

from app.schemas.resume import ProviderIngestionSummary


class BatchRunResponse(BaseModel):
    batch_id: str
    started_at: str
    finished_at: str | None
    status: str
    total_files_seen: int
    ingested_count: int
    updated_count: int
    skipped_count: int
    failed_count: int
    parsed_count: int
    fallback_count: int
    error_message: str | None = None
    providers: list[ProviderIngestionSummary] = Field(default_factory=list)


class BatchRunListResponse(BaseModel):
    runs: list[BatchRunResponse]


class ActiveBatchRunResponse(BaseModel):
    is_running: bool
    batch_id: str | None = None
    started_at: str | None = None
    status: str | None = None

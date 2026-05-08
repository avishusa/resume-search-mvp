from pydantic import BaseModel


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


class BatchRunListResponse(BaseModel):
    runs: list[BatchRunResponse]

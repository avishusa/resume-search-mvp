from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    resume_id: str
    file_name: str
    mime_type: str
    extraction_status: str
    extracted_text_preview: str


class ResumeListItem(BaseModel):
    resume_id: str
    provider_name: str | None = None
    source_id: str | None = None
    file_name: str
    source_path: str | None
    file_type: str | None = None
    file_hash: str | None = None
    last_modified: str | None = None
    extraction_status: str
    parsing_status: str | None = None
    parser_used: str | None = None
    parsing_error: str | None = None
    ollama_error: str | None = None
    ollama_raw_response_preview: str | None = None
    ollama_model: str | None = None
    parsed_at: str | None = None
    ingested_at: str | None = None
    extracted_text_preview: str
    extraction_duration_seconds: float | None = None
    parsing_duration_seconds: float | None = None
    total_processing_duration_seconds: float | None = None
    llm_input_chars: int | None = None
    digest_used: bool | None = None
    processing_started_at: str | None = None
    processing_finished_at: str | None = None
    parsing_started_at: str | None = None
    parsing_finished_at: str | None = None
    task_id: int | None = None
    worker_slot: str | None = None
    ollama_request_duration_seconds: float | None = None
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    current_title: str | None = None
    skills: list[str] = Field(default_factory=list)
    total_experience_years: float | None = None
    experience_extraction_method: str | None = None
    experience_date_ranges: list[str] = Field(default_factory=list)
    companies: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    resume_summary: str = ""
    confidence_score: float | None = None


class ResumeIngestionItem(BaseModel):
    resume_id: str
    provider_name: str | None = None
    source_id: str | None = None
    file_name: str
    source_path: str | None
    file_type: str
    file_hash: str | None = None
    last_modified: str | None = None
    extraction_status: str
    parsing_status: str | None = None
    parser_used: str | None = None
    parsing_error: str | None = None
    ollama_error: str | None = None
    ollama_raw_response_preview: str | None = None
    ollama_model: str | None = None
    parsed_at: str | None = None
    ingested_at: str | None = None
    extracted_text_preview: str
    extraction_duration_seconds: float | None = None
    parsing_duration_seconds: float | None = None
    total_processing_duration_seconds: float | None = None
    llm_input_chars: int | None = None
    digest_used: bool | None = None
    processing_started_at: str | None = None
    processing_finished_at: str | None = None
    parsing_started_at: str | None = None
    parsing_finished_at: str | None = None
    task_id: int | None = None
    worker_slot: str | None = None
    ollama_request_duration_seconds: float | None = None


class ProviderIngestionSummary(BaseModel):
    provider_name: str
    total_files_seen: int
    ingested_count: int
    updated_count: int = 0
    skipped_count: int
    failed_count: int
    parsed_count: int = 0
    fallback_count: int = 0
    error_message: str | None = None


class LocalDriveIngestionResponse(BaseModel):
    total_files_seen: int
    ingested_count: int
    updated_count: int = 0
    skipped_count: int
    failed_count: int
    parsed_count: int = 0
    fallback_count: int = 0
    resumes: list[ResumeIngestionItem]
    providers: list[ProviderIngestionSummary] = Field(default_factory=list)
    configured_concurrency: int = 1
    max_observed_parallel_tasks: int = 0
    total_batch_duration_seconds: float | None = None
    total_ollama_duration_seconds_sum: float = 0
    average_ollama_duration_seconds: float | None = None

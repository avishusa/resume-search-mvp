from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    resume_id: str
    file_name: str
    mime_type: str
    extraction_status: str
    extracted_text_preview: str


class ResumeListItem(BaseModel):
    resume_id: str
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
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    current_title: str | None = None
    skills: list[str] = Field(default_factory=list)
    total_experience_years: float | None = None
    companies: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    resume_summary: str = ""
    confidence_score: float | None = None


class ResumeIngestionItem(BaseModel):
    resume_id: str
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


class LocalDriveIngestionResponse(BaseModel):
    total_files_seen: int
    ingested_count: int
    updated_count: int = 0
    skipped_count: int
    failed_count: int
    parsed_count: int = 0
    fallback_count: int = 0
    resumes: list[ResumeIngestionItem]

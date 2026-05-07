from pydantic import BaseModel


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
    extraction_status: str
    extracted_text_preview: str


class ResumeIngestionItem(BaseModel):
    resume_id: str
    file_name: str
    source_path: str | None
    mime_type: str
    extraction_status: str
    extracted_text_preview: str


class LocalDriveIngestionResponse(BaseModel):
    total_files_seen: int
    ingested_count: int
    skipped_count: int
    failed_count: int
    resumes: list[ResumeIngestionItem]

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.container import batch_processing_service, resume_repository, resume_upload_service
from app.schemas.resume import (
    LocalDriveIngestionResponse,
    ResumeListItem,
    ResumeUploadResponse,
)
from app.services.resume_ingestion_service import UnsupportedResumeFileTypeError
from app.services.batch_processing_service import BatchAlreadyRunningError

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(file: UploadFile = File(...)) -> ResumeUploadResponse:
    file_bytes = await file.read()

    try:
        return resume_upload_service.upload_resume(
            file_name=file.filename or "uploaded-resume",
            mime_type=file.content_type,
            file_bytes=file_bytes,
        )
    except UnsupportedResumeFileTypeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.post("/ingest-local-drive", response_model=LocalDriveIngestionResponse)
def ingest_local_drive(force: bool = False) -> LocalDriveIngestionResponse:
    try:
        _batch_run, summary = batch_processing_service.run_local_drive_batch(force=force)
    except BatchAlreadyRunningError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    return summary


@router.get("", response_model=list[ResumeListItem])
def list_resumes() -> list[ResumeListItem]:
    return [
        ResumeListItem(
            resume_id=record.resume_id,
            file_name=record.file_name,
            source_path=record.source_path,
            file_type=record.file_type,
            file_hash=record.file_hash,
            last_modified=record.last_modified.isoformat()
            if record.last_modified
            else None,
            extraction_status=record.extraction_status,
            parsing_status=record.parsing_status,
            parser_used=record.parser_used,
            parsing_error=record.parsing_error,
            ollama_error=record.ollama_error,
            ollama_raw_response_preview=record.ollama_raw_response_preview,
            ollama_model=record.ollama_model,
            parsed_at=record.parsed_at.isoformat() if record.parsed_at else None,
            ingested_at=record.ingested_at.isoformat(),
            extracted_text_preview=record.extracted_text_preview,
            candidate_name=record.candidate_profile.candidate_name
            if record.candidate_profile
            else None,
            email=record.candidate_profile.email if record.candidate_profile else None,
            phone=record.candidate_profile.phone if record.candidate_profile else None,
            current_title=record.candidate_profile.current_title
            if record.candidate_profile
            else None,
            skills=record.candidate_profile.skills if record.candidate_profile else [],
            total_experience_years=record.candidate_profile.total_experience_years
            if record.candidate_profile
            else None,
            experience_extraction_method=record.candidate_profile.experience_extraction_method
            if record.candidate_profile
            else None,
            experience_date_ranges=record.candidate_profile.experience_date_ranges
            if record.candidate_profile
            else [],
            companies=record.candidate_profile.companies if record.candidate_profile else [],
            education=record.candidate_profile.education if record.candidate_profile else [],
            resume_summary=record.candidate_profile.resume_summary
            if record.candidate_profile
            else "",
            confidence_score=record.candidate_profile.confidence_score
            if record.candidate_profile
            else None,
        )
        for record in resume_repository.list_all()
    ]

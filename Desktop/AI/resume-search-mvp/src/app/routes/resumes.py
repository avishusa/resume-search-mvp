from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.container import resume_ingestion_service, resume_repository, resume_upload_service
from app.schemas.resume import (
    LocalDriveIngestionResponse,
    ResumeListItem,
    ResumeUploadResponse,
)
from app.services.resume_ingestion_service import UnsupportedResumeFileTypeError

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
def ingest_local_drive() -> LocalDriveIngestionResponse:
    return resume_ingestion_service.ingest_local_drive()


@router.get("", response_model=list[ResumeListItem])
def list_resumes() -> list[ResumeListItem]:
    return [
        ResumeListItem(
            resume_id=record.resume_id,
            file_name=record.file_name,
            source_path=record.source_path,
            extraction_status=record.extraction_status,
            extracted_text_preview=record.extracted_text[:300],
        )
        for record in resume_repository.list_all()
    ]

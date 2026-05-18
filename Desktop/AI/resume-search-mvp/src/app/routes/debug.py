from fastapi import APIRouter

from app.container import debug_service
from app.schemas.debug import (
    OllamaDebugResponse,
    ParseResumeTextDebugRequest,
    ParseResumeTextDebugResponse,
    StorageProviderDebugResponse,
)

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/ollama", response_model=OllamaDebugResponse)
def debug_ollama() -> OllamaDebugResponse:
    return debug_service.check_ollama()


@router.post("/parse-resume-text", response_model=ParseResumeTextDebugResponse)
def debug_parse_resume_text(
    request: ParseResumeTextDebugRequest,
) -> ParseResumeTextDebugResponse:
    return debug_service.parse_resume_text(request.text)


@router.get("/storage-provider", response_model=StorageProviderDebugResponse)
def debug_storage_provider() -> StorageProviderDebugResponse:
    return debug_service.check_storage_providers()

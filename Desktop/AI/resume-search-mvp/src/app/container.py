from app.config import get_settings
from app.parsing.ollama import OllamaResumeParserProvider
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.repositories.batch_run_repository import BatchRunRepository
from app.repositories.sqlalchemy_resume_repository import SQLAlchemyResumeRepository
from app.services.batch_processing_service import ResumeBatchProcessingService
from app.services.candidate_profile_service import CandidateProfileService
from app.services.debug_service import DebugService
from app.services.resume_batch_processor import ResumeBatchProcessor
from app.services.resume_ingestion_service import ResumeIngestionService
from app.services.resume_search_service import ResumeSearchService
from app.services.resume_service import ResumeUploadService
from app.storage.factory import (
    create_local_resume_storage_provider,
    create_resume_storage_provider,
    create_resume_storage_providers,
)

settings = get_settings()
resume_repository = SQLAlchemyResumeRepository()
batch_run_repository = BatchRunRepository()
resume_storage_provider = create_resume_storage_provider(settings)
resume_storage_providers = create_resume_storage_providers(settings)
local_resume_storage_provider = create_local_resume_storage_provider(settings)

skill_catalog = [
    skill.strip()
    for skill in settings.skill_catalog.split(",")
    if skill.strip()
]
fallback_resume_parser_provider = RuleBasedResumeParserProvider(
    skill_catalog=skill_catalog,
    contact_only=True,
)

if settings.resume_parser_provider == "rule_based":
    primary_resume_parser_provider = fallback_resume_parser_provider
else:
    primary_resume_parser_provider = OllamaResumeParserProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        max_resume_chars=settings.ollama_max_resume_chars,
        use_resume_digest=settings.ollama_use_resume_digest,
        temperature=settings.ollama_temperature,
        num_predict=settings.ollama_num_predict,
        num_ctx=settings.ollama_num_ctx,
    )

candidate_profile_service = CandidateProfileService(
    primary_parser=primary_resume_parser_provider,
    fallback_parser=fallback_resume_parser_provider,
)
debug_service = DebugService(
    settings=settings,
    candidate_profile_service=candidate_profile_service,
)
resume_ingestion_service = ResumeIngestionService(
    repository=resume_repository,
    candidate_profile_service=candidate_profile_service,
)
resume_batch_processor = ResumeBatchProcessor(
    repository=resume_repository,
    candidate_profile_service=candidate_profile_service,
    storage_provider=resume_storage_provider,
    storage_providers=resume_storage_providers,
    parse_concurrency=settings.resume_parse_concurrency,
)
local_resume_batch_processor = ResumeBatchProcessor(
    repository=resume_repository,
    candidate_profile_service=candidate_profile_service,
    storage_provider=local_resume_storage_provider,
    parse_concurrency=settings.resume_parse_concurrency,
)
batch_processing_service = ResumeBatchProcessingService(
    batch_processor=resume_batch_processor,
    local_batch_processor=local_resume_batch_processor,
    batch_run_repository=batch_run_repository,
)
resume_upload_service = ResumeUploadService(ingestion_service=resume_ingestion_service)
resume_search_service = ResumeSearchService(repository=resume_repository)

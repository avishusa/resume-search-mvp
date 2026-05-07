from app.config import get_settings
from app.parsing.ollama import OllamaResumeParserProvider
from app.parsing.rule_based import RuleBasedResumeParserProvider
from app.repositories.resume_repository import InMemoryResumeRepository
from app.services.candidate_profile_service import CandidateProfileService
from app.services.debug_service import DebugService
from app.services.resume_batch_processor import ResumeBatchProcessor
from app.services.resume_ingestion_service import ResumeIngestionService
from app.services.resume_search_service import ResumeSearchService
from app.services.resume_service import ResumeUploadService

settings = get_settings()
resume_repository = InMemoryResumeRepository()

skill_catalog = [
    skill.strip()
    for skill in settings.skill_catalog.split(",")
    if skill.strip()
]
fallback_resume_parser_provider = RuleBasedResumeParserProvider(
    skill_catalog=skill_catalog
)

if settings.resume_parser_provider == "rule_based":
    primary_resume_parser_provider = fallback_resume_parser_provider
else:
    primary_resume_parser_provider = OllamaResumeParserProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        max_resume_chars=settings.ollama_max_resume_chars,
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
)
resume_upload_service = ResumeUploadService(ingestion_service=resume_ingestion_service)
resume_search_service = ResumeSearchService(repository=resume_repository)

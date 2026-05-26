from dataclasses import dataclass

from app.parsing.base import ResumeParserError, ResumeParserProvider
from app.schemas.candidate import CandidateProfile
from app.services.experience_extractor import ExperienceExtractor


@dataclass(frozen=True)
class CandidateProfileParseResult:
    profile: CandidateProfile
    parsing_error: str | None = None
    ollama_error: str | None = None
    ollama_raw_response_preview: str | None = None
    ollama_model: str | None = None
    llm_input_chars: int | None = None
    digest_used: bool | None = None
    ollama_request_duration_seconds: float | None = None


class CandidateProfileService:
    def __init__(
        self,
        primary_parser: ResumeParserProvider,
        fallback_parser: ResumeParserProvider,
        experience_extractor: ExperienceExtractor | None = None,
    ) -> None:
        self._primary_parser = primary_parser
        self._fallback_parser = fallback_parser
        self._experience_extractor = experience_extractor or ExperienceExtractor()

    def parse(self, resume_text: str) -> CandidateProfile:
        return self.parse_with_metadata(resume_text).profile

    def parse_with_metadata(self, resume_text: str) -> CandidateProfileParseResult:
        try:
            profile = self._primary_parser.parse(resume_text)
            profile = self._add_experience_if_needed(profile, resume_text)
            return CandidateProfileParseResult(
                profile=profile,
                ollama_raw_response_preview=getattr(
                    self._primary_parser,
                    "last_raw_response_preview",
                    None,
                ),
                ollama_model=getattr(self._primary_parser, "last_ollama_model", None),
                llm_input_chars=getattr(
                    self._primary_parser,
                    "last_llm_input_chars",
                    None,
                ),
                digest_used=getattr(self._primary_parser, "last_digest_used", None),
                ollama_request_duration_seconds=getattr(
                    self._primary_parser,
                    "last_ollama_request_duration_seconds",
                    None,
                ),
            )
        except ResumeParserError as error:
            fallback_profile = self._fallback_parser.parse(resume_text)
            return CandidateProfileParseResult(
                profile=fallback_profile,
                parsing_error=str(error),
                ollama_error=str(error),
                ollama_raw_response_preview=error.raw_response_preview,
                ollama_model=error.ollama_model,
                llm_input_chars=error.llm_input_chars,
                digest_used=error.digest_used,
                ollama_request_duration_seconds=error.ollama_request_duration_seconds,
            )

    def _add_experience_if_needed(
        self,
        profile: CandidateProfile,
        resume_text: str,
    ) -> CandidateProfile:
        extraction = self._experience_extractor.extract(resume_text)
        if extraction.method == "unknown":
            return profile.model_copy(
                update={
                    "experience_extraction_method": profile.experience_extraction_method,
                    "experience_date_ranges": profile.experience_date_ranges,
                }
            )

        if extraction.method == "explicit_text":
            return profile.model_copy(
                update={
                    "total_experience_years": extraction.total_years,
                    "experience_extraction_method": extraction.method,
                    "experience_date_ranges": extraction.date_ranges,
                }
            )

        if profile.total_experience_years is not None:
            return profile

        return profile.model_copy(
            update={
                "total_experience_years": extraction.total_years,
                "experience_extraction_method": extraction.method,
                "experience_date_ranges": extraction.date_ranges,
            }
        )

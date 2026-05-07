from dataclasses import dataclass

from app.parsing.base import ResumeParserError, ResumeParserProvider
from app.schemas.candidate import CandidateProfile


@dataclass(frozen=True)
class CandidateProfileParseResult:
    profile: CandidateProfile
    parsing_error: str | None = None
    ollama_error: str | None = None
    ollama_raw_response_preview: str | None = None
    ollama_model: str | None = None


class CandidateProfileService:
    def __init__(
        self,
        primary_parser: ResumeParserProvider,
        fallback_parser: ResumeParserProvider,
    ) -> None:
        self._primary_parser = primary_parser
        self._fallback_parser = fallback_parser

    def parse(self, resume_text: str) -> CandidateProfile:
        return self.parse_with_metadata(resume_text).profile

    def parse_with_metadata(self, resume_text: str) -> CandidateProfileParseResult:
        try:
            profile = self._primary_parser.parse(resume_text)
            return CandidateProfileParseResult(
                profile=profile,
                ollama_raw_response_preview=getattr(
                    self._primary_parser,
                    "last_raw_response_preview",
                    None,
                ),
                ollama_model=getattr(self._primary_parser, "last_ollama_model", None),
            )
        except ResumeParserError as error:
            fallback_profile = self._fallback_parser.parse(resume_text)
            return CandidateProfileParseResult(
                profile=fallback_profile,
                parsing_error=str(error),
                ollama_error=str(error),
                ollama_raw_response_preview=error.raw_response_preview,
                ollama_model=error.ollama_model,
            )

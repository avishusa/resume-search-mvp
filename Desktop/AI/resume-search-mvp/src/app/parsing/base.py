from typing import Protocol

from app.schemas.candidate import CandidateProfile


class ResumeParserError(Exception):
    def __init__(
        self,
        message: str,
        raw_response_preview: str | None = None,
        ollama_model: str | None = None,
    ) -> None:
        super().__init__(message)
        self.raw_response_preview = raw_response_preview
        self.ollama_model = ollama_model


class ResumeParserProvider(Protocol):
    parser_name: str

    def parse(self, resume_text: str) -> CandidateProfile:
        """Parse extracted resume text into a structured candidate profile."""

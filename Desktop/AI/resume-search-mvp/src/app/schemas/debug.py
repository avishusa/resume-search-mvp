from typing import Any

from pydantic import BaseModel


class OllamaDebugResponse(BaseModel):
    resume_parser_provider: str
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: int
    ollama_max_resume_chars: int
    ollama_reachable: bool
    test_generation_success: bool
    error: str | None = None


class ParseResumeTextDebugRequest(BaseModel):
    text: str


class ParseResumeTextDebugResponse(BaseModel):
    parser_used: str
    profile: dict[str, Any]
    parsing_error: str | None = None
    ollama_error: str | None = None
    ollama_raw_response_preview: str | None = None
    ollama_model: str | None = None

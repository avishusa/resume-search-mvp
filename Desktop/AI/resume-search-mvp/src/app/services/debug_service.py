import json

import httpx

from app.config import Settings
from app.schemas.debug import OllamaDebugResponse, ParseResumeTextDebugResponse
from app.services.candidate_profile_service import CandidateProfileService


class DebugService:
    def __init__(
        self,
        settings: Settings,
        candidate_profile_service: CandidateProfileService,
    ) -> None:
        self._settings = settings
        self._candidate_profile_service = candidate_profile_service

    def check_ollama(self) -> OllamaDebugResponse:
        ollama_reachable = False
        test_generation_success = False
        error = None

        try:
            with httpx.Client(timeout=self._settings.ollama_timeout_seconds) as client:
                response = client.post(
                    f"{self._settings.ollama_base_url.rstrip('/')}/api/generate",
                    json={
                        "model": self._settings.ollama_model,
                        "prompt": 'Return only JSON: {"status":"ok"}',
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()

            ollama_reachable = True
            response_body = response.json()
            raw_generation = response_body.get("response")
            if not isinstance(raw_generation, str):
                raise ValueError("Ollama response did not include a response string.")

            parsed_generation = json.loads(raw_generation)
            test_generation_success = parsed_generation.get("status") == "ok"
            if not test_generation_success:
                error = "Ollama JSON response did not contain status=ok."
        except Exception as exception:
            error = str(exception)

        return OllamaDebugResponse(
            resume_parser_provider=self._settings.resume_parser_provider,
            ollama_base_url=self._settings.ollama_base_url,
            ollama_model=self._settings.ollama_model,
            ollama_timeout_seconds=self._settings.ollama_timeout_seconds,
            ollama_max_resume_chars=self._settings.ollama_max_resume_chars,
            ollama_reachable=ollama_reachable,
            test_generation_success=test_generation_success,
            error=error,
        )

    def parse_resume_text(self, resume_text: str) -> ParseResumeTextDebugResponse:
        parse_result = self._candidate_profile_service.parse_with_metadata(resume_text)
        profile = parse_result.profile
        return ParseResumeTextDebugResponse(
            parser_used=profile.parser_used,
            profile=profile.model_dump(),
            parsing_error=parse_result.parsing_error,
            ollama_error=parse_result.ollama_error,
            ollama_raw_response_preview=parse_result.ollama_raw_response_preview,
            ollama_model=parse_result.ollama_model,
        )

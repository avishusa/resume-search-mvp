import json
import re

import httpx
from pydantic import ValidationError

from app.parsing.base import ResumeParserError
from app.parsing.text_cleaning import clean_resume_text_for_llm
from app.schemas.candidate import CandidateProfile


OLLAMA_RETRY_MAX_RESUME_CHARS = 4000


class OllamaResumeParserProvider:
    parser_name = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int,
        max_resume_chars: int = 12000,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_resume_chars = max_resume_chars
        self.last_raw_response_preview: str | None = None
        self.last_ollama_model: str = model
        self.last_cleaned_text_length: int | None = None
        self.last_prompt_text_length: int | None = None

    def parse(self, resume_text: str) -> CandidateProfile:
        self.last_raw_response_preview = None
        self.last_cleaned_text_length = None
        self.last_prompt_text_length = None
        cleaned_resume_text = clean_resume_text_for_llm(resume_text)
        self.last_cleaned_text_length = len(cleaned_resume_text)
        try:
            raw_profile_json = self._generate_profile_json(
                cleaned_resume_text=cleaned_resume_text,
                max_resume_chars=self._max_resume_chars,
            )
            self.last_raw_response_preview = raw_profile_json[:500]

            profile_data = json.loads(raw_profile_json)
            if not isinstance(profile_data, dict):
                raise ResumeParserError(
                    "Ollama response JSON must be an object.",
                    raw_response_preview=self.last_raw_response_preview,
                    ollama_model=self._model,
                    cleaned_text_length=self.last_cleaned_text_length,
                    prompt_text_length=self.last_prompt_text_length,
                )

            profile_data = self._normalize_profile_data(profile_data)
            profile_data["parsing_status"] = "parsed"
            profile_data["parser_used"] = "ollama"
            return CandidateProfile.model_validate(profile_data)
        except (httpx.HTTPError, json.JSONDecodeError, ValidationError, ResumeParserError) as error:
            raw_response_preview = getattr(
                error,
                "raw_response_preview",
                self.last_raw_response_preview,
            )
            cleaned_text_length = getattr(
                error,
                "cleaned_text_length",
                self.last_cleaned_text_length,
            )
            prompt_text_length = getattr(
                error,
                "prompt_text_length",
                self.last_prompt_text_length,
            )
            raise ResumeParserError(
                f"Ollama resume parsing failed: {error}",
                raw_response_preview=raw_response_preview,
                ollama_model=self._model,
                cleaned_text_length=cleaned_text_length,
                prompt_text_length=prompt_text_length,
            ) from error

    def _generate_profile_json(
        self,
        cleaned_resume_text: str,
        max_resume_chars: int,
    ) -> str:
        try:
            return self._request_profile_json(cleaned_resume_text, max_resume_chars)
        except ResumeParserError as first_error:
            if not self._should_retry_with_shorter_text(first_error, max_resume_chars):
                raise

            try:
                return self._request_profile_json(
                    cleaned_resume_text,
                    min(OLLAMA_RETRY_MAX_RESUME_CHARS, max_resume_chars),
                )
            except ResumeParserError as retry_error:
                retry_error.args = (
                    f"{first_error}; retry_error={retry_error}",
                )
                raise retry_error from first_error

    def _request_profile_json(
        self,
        cleaned_resume_text: str,
        max_resume_chars: int,
    ) -> str:
        truncated_resume_text = cleaned_resume_text[:max_resume_chars]
        prompt = self._build_prompt(truncated_resume_text)
        self.last_prompt_text_length = len(prompt)

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            response_preview = error.response.text[:500] if error.response else None
            self.last_raw_response_preview = response_preview
            raise ResumeParserError(
                self._build_http_error_message(
                    error=error,
                    cleaned_text_length=len(cleaned_resume_text),
                    prompt_text_length=len(prompt),
                    input_text_length=len(truncated_resume_text),
                    max_resume_chars=max_resume_chars,
                    response_preview=response_preview,
                ),
                raw_response_preview=response_preview,
                ollama_model=self._model,
                cleaned_text_length=len(cleaned_resume_text),
                prompt_text_length=len(prompt),
            ) from error

        response_body = response.json()
        raw_profile_json = response_body.get("response")
        if not isinstance(raw_profile_json, str):
            raise ResumeParserError(
                "Ollama response did not include JSON text.",
                ollama_model=self._model,
                cleaned_text_length=len(cleaned_resume_text),
                prompt_text_length=len(prompt),
            )
        return raw_profile_json

    def _should_retry_with_shorter_text(
        self,
        error: ResumeParserError,
        max_resume_chars: int,
    ) -> bool:
        return "HTTP 500" in str(error) and max_resume_chars > OLLAMA_RETRY_MAX_RESUME_CHARS

    def _build_http_error_message(
        self,
        error: httpx.HTTPStatusError,
        cleaned_text_length: int,
        prompt_text_length: int,
        input_text_length: int,
        max_resume_chars: int,
        response_preview: str | None,
    ) -> str:
        response = error.response
        return (
            f"Ollama HTTP {response.status_code} error; "
            f"model={self._model}; "
            f"cleaned_text_chars={cleaned_text_length}; "
            f"prompt_chars={prompt_text_length}; "
            f"input_chars={input_text_length}; "
            f"max_resume_chars={max_resume_chars}; "
            f"response_preview={response_preview or ''}"
        )

    def _normalize_profile_data(self, profile_data: dict) -> dict:
        normalized_data = dict(profile_data)
        for key in [
            "candidate_name",
            "phone",
            "current_title",
            "resume_summary",
        ]:
            normalized_data[key] = self._normalize_string_value(normalized_data.get(key))
        normalized_data["email"] = self._normalize_email_value(
            normalized_data.get("email")
        )

        normalized_data["skills"] = self._normalize_string_list(
            normalized_data.get("skills")
        )
        normalized_data["companies"] = self._normalize_string_list(
            normalized_data.get("companies")
        )
        normalized_data["education"] = self._normalize_string_list(
            normalized_data.get("education")
        )
        normalized_data["total_experience_years"] = self._normalize_optional_number(
            normalized_data.get("total_experience_years")
        )
        normalized_data["confidence_score"] = self._normalize_confidence_score(
            normalized_data.get("confidence_score"),
            normalized_data,
        )
        return normalized_data

    def _normalize_string_value(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, list):
            for item in value:
                normalized_item = self._normalize_string_value(item)
                if normalized_item:
                    return normalized_item
            return None
        if not isinstance(value, str):
            return None
        cleaned_value = value.strip()
        return cleaned_value or None

    def _normalize_email_value(self, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, list):
            for item in value:
                normalized_email = self._normalize_email_value(item)
                if normalized_email:
                    return normalized_email
            return None
        if not isinstance(value, str):
            return None

        match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", value.strip())
        return match.group(0) if match else None

    def _normalize_string_list(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = value.split(",") if "," in value else [value]
        if not isinstance(value, list):
            return []

        normalized_values: list[str] = []
        seen_values: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            cleaned_item = item.strip()
            if not cleaned_item:
                continue
            dedupe_key = cleaned_item.lower()
            if dedupe_key in seen_values:
                continue
            seen_values.add(dedupe_key)
            normalized_values.append(cleaned_item)
        return normalized_values

    def _normalize_optional_number(self, value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            cleaned_value = value.strip()
            if not cleaned_value:
                return None
            try:
                return float(cleaned_value)
            except ValueError:
                return None
        return None

    def _normalize_confidence_score(self, value: object, profile_data: dict) -> float:
        numeric_value = self._try_parse_float(value)
        if numeric_value is None:
            numeric_value = self._calculate_confidence_score(profile_data)
        return self._clamp_confidence_score(numeric_value)

    def _try_parse_float(self, value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            cleaned_value = value.strip()
            if not cleaned_value:
                return None
            try:
                return float(cleaned_value)
            except ValueError:
                return None
        return None

    def _calculate_confidence_score(self, profile_data: dict) -> float:
        score = 0.1
        if profile_data.get("candidate_name"):
            score += 0.2
        if profile_data.get("email"):
            score += 0.2
        if profile_data.get("phone"):
            score += 0.15
        if profile_data.get("current_title"):
            score += 0.2
        if profile_data.get("skills"):
            score += 0.15
        return self._clamp_confidence_score(score)

    def _clamp_confidence_score(self, value: float) -> float:
        if not isinstance(value, int | float):
            raise ResumeParserError("confidence_score must be numeric.")
        return min(max(float(value), 0), 1)

    def _build_prompt(self, resume_text: str) -> str:
        return f"""You are an expert resume information extraction engine.

Extract structured candidate information from the resume text.

Rules:
- Return ONLY valid JSON.
- Do not include markdown.
- Do not include explanation.
- Do not guess.
- Extract only information explicitly present in the resume.
- If a field is missing, return null or [].
- Prefer the most recent/current role for current_title.
- Do not infer title from skills.
- Do not infer skills that are not explicitly listed or clearly mentioned.
- Normalize outputs.
- confidence_score must be a number between 0 and 1.
- Do not return confidence_score as a string.
- Do not return "high", "medium", or "low" for confidence_score.

JSON schema:
{{
  "candidate_name": string or null,
  "email": string or null,
  "phone": string or null,
  "current_title": string or null,
  "skills": [string],
  "total_experience_years": number or null,
  "companies": [string],
  "education": [string],
  "resume_summary": string,
  "confidence_score": number
}}

Resume text:
{resume_text}
"""

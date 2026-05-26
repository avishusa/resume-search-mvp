import json
import re
from threading import local
from time import perf_counter

import httpx
from pydantic import ValidationError

from app.parsing.base import ResumeParserError
from app.parsing.text_cleaning import (
    build_resume_digest_for_llm,
    clean_resume_text_for_llm,
)
from app.schemas.candidate import CandidateProfile


OLLAMA_RETRY_MAX_RESUME_CHARS = 4000


class OllamaResumeParserProvider:
    parser_name = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int,
        max_resume_chars: int = 6000,
        use_resume_digest: bool = True,
        temperature: float = 0,
        num_predict: int = 600,
        num_ctx: int | None = None,
    ) -> None:
        self._thread_state = local()
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_resume_chars = max_resume_chars
        self._use_resume_digest = use_resume_digest
        self._temperature = temperature
        self._num_predict = num_predict
        self._num_ctx = num_ctx
        self.last_raw_response_preview: str | None = None
        self.last_ollama_model: str = model
        self.last_cleaned_text_length: int | None = None
        self.last_prompt_text_length: int | None = None
        self.last_llm_input_chars: int | None = None
        self.last_digest_used: bool = use_resume_digest
        self.last_ollama_request_duration_seconds: float | None = None

    @property
    def last_raw_response_preview(self) -> str | None:
        return getattr(self._thread_state, "last_raw_response_preview", None)

    @last_raw_response_preview.setter
    def last_raw_response_preview(self, value: str | None) -> None:
        self._thread_state.last_raw_response_preview = value

    @property
    def last_cleaned_text_length(self) -> int | None:
        return getattr(self._thread_state, "last_cleaned_text_length", None)

    @last_cleaned_text_length.setter
    def last_cleaned_text_length(self, value: int | None) -> None:
        self._thread_state.last_cleaned_text_length = value

    @property
    def last_prompt_text_length(self) -> int | None:
        return getattr(self._thread_state, "last_prompt_text_length", None)

    @last_prompt_text_length.setter
    def last_prompt_text_length(self, value: int | None) -> None:
        self._thread_state.last_prompt_text_length = value

    @property
    def last_llm_input_chars(self) -> int | None:
        return getattr(self._thread_state, "last_llm_input_chars", None)

    @last_llm_input_chars.setter
    def last_llm_input_chars(self, value: int | None) -> None:
        self._thread_state.last_llm_input_chars = value

    @property
    def last_digest_used(self) -> bool:
        return getattr(self._thread_state, "last_digest_used", self._use_resume_digest)

    @last_digest_used.setter
    def last_digest_used(self, value: bool) -> None:
        self._thread_state.last_digest_used = value

    @property
    def last_ollama_request_duration_seconds(self) -> float | None:
        return getattr(
            self._thread_state,
            "last_ollama_request_duration_seconds",
            None,
        )

    @last_ollama_request_duration_seconds.setter
    def last_ollama_request_duration_seconds(self, value: float | None) -> None:
        self._thread_state.last_ollama_request_duration_seconds = value

    def parse(self, resume_text: str) -> CandidateProfile:
        self.last_raw_response_preview = None
        self.last_cleaned_text_length = None
        self.last_prompt_text_length = None
        self.last_llm_input_chars = None
        self.last_digest_used = self._use_resume_digest
        self.last_ollama_request_duration_seconds = 0
        cleaned_resume_text = clean_resume_text_for_llm(resume_text)
        self.last_cleaned_text_length = len(cleaned_resume_text)
        llm_resume_text = (
            build_resume_digest_for_llm(
                cleaned_resume_text,
                max_chars=self._max_resume_chars,
            )
            if self._use_resume_digest
            else cleaned_resume_text
        )
        try:
            raw_profile_json = self._generate_profile_json(
                cleaned_resume_text=llm_resume_text,
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
                    llm_input_chars=self.last_llm_input_chars,
                    digest_used=self.last_digest_used,
                    ollama_request_duration_seconds=self.last_ollama_request_duration_seconds,
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
            llm_input_chars = getattr(
                error,
                "llm_input_chars",
                self.last_llm_input_chars,
            )
            digest_used = getattr(
                error,
                "digest_used",
                self.last_digest_used,
            )
            ollama_request_duration_seconds = getattr(
                error,
                "ollama_request_duration_seconds",
                self.last_ollama_request_duration_seconds,
            )
            raise ResumeParserError(
                f"Ollama resume parsing failed: {error}",
                raw_response_preview=raw_response_preview,
                ollama_model=self._model,
                cleaned_text_length=cleaned_text_length,
                prompt_text_length=prompt_text_length,
                llm_input_chars=llm_input_chars,
                digest_used=digest_used,
                ollama_request_duration_seconds=ollama_request_duration_seconds,
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
        self.last_llm_input_chars = len(truncated_resume_text)
        prompt = self._build_prompt(truncated_resume_text)
        self.last_prompt_text_length = len(prompt)

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                request_start = perf_counter()
                response = client.post(
                    f"{self._base_url}/api/generate",
                    json=self._build_generate_payload(prompt),
                )
                self._add_ollama_request_duration(perf_counter() - request_start)
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
                llm_input_chars=len(truncated_resume_text),
                digest_used=self.last_digest_used,
                ollama_request_duration_seconds=self.last_ollama_request_duration_seconds,
            ) from error
        except httpx.HTTPError as error:
            self._add_ollama_request_duration(
                perf_counter() - request_start
                if "request_start" in locals()
                else 0
            )
            raise error

        response_body = response.json()
        raw_profile_json = response_body.get("response")
        if not isinstance(raw_profile_json, str):
            raise ResumeParserError(
                "Ollama response did not include JSON text.",
                ollama_model=self._model,
                cleaned_text_length=len(cleaned_resume_text),
                prompt_text_length=len(prompt),
                llm_input_chars=len(truncated_resume_text),
                digest_used=self.last_digest_used,
                ollama_request_duration_seconds=self.last_ollama_request_duration_seconds,
            )
        return raw_profile_json

    def _add_ollama_request_duration(self, duration_seconds: float) -> None:
        current_duration = self.last_ollama_request_duration_seconds or 0
        self.last_ollama_request_duration_seconds = round(
            current_duration + max(duration_seconds, 0),
            4,
        )

    def _build_generate_payload(self, prompt: str) -> dict:
        options = {
            "temperature": self._temperature,
            "num_predict": self._num_predict,
        }
        if self._num_ctx is not None:
            options["num_ctx"] = self._num_ctx

        return {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": options,
        }

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
        return f"""Extract structured resume data.

Return ONLY valid JSON. No markdown. No explanation. Do not guess.
Use only facts explicitly present in the resume. Missing scalar fields must be null. Missing array fields must be [].
Prefer the most recent/current role only when explicitly present. Do not infer title from skills.
confidence_score must be a numeric value from 0 to 1. Do not return "high", "medium", or "low".
email and phone must be string or null. skills, companies, and education must be arrays.

Return exactly this JSON schema:
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

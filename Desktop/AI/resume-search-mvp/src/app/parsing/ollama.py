import json

import httpx
from pydantic import ValidationError

from app.parsing.base import ResumeParserError
from app.schemas.candidate import CandidateProfile


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

    def parse(self, resume_text: str) -> CandidateProfile:
        self.last_raw_response_preview = None
        try:
            truncated_resume_text = resume_text[: self._max_resume_chars]
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": self._build_prompt(truncated_resume_text),
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()

            response_body = response.json()
            raw_profile_json = response_body.get("response")
            if not isinstance(raw_profile_json, str):
                raise ResumeParserError(
                    "Ollama response did not include JSON text.",
                    ollama_model=self._model,
                )

            self.last_raw_response_preview = raw_profile_json[:500]

            profile_data = json.loads(raw_profile_json)
            if not isinstance(profile_data, dict):
                raise ResumeParserError(
                    "Ollama response JSON must be an object.",
                    raw_response_preview=self.last_raw_response_preview,
                    ollama_model=self._model,
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
            raise ResumeParserError(
                f"Ollama resume parsing failed: {error}",
                raw_response_preview=raw_response_preview,
                ollama_model=self._model,
            ) from error

    def _normalize_profile_data(self, profile_data: dict) -> dict:
        normalized_data = dict(profile_data)
        for key in [
            "candidate_name",
            "email",
            "phone",
            "current_title",
            "resume_summary",
        ]:
            normalized_data[key] = self._normalize_string_value(normalized_data.get(key))

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
        if not isinstance(value, str):
            return value
        cleaned_value = value.strip()
        return cleaned_value or None

    def _normalize_string_list(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
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

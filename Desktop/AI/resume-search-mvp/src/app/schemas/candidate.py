from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CandidateProfile(BaseModel):
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    current_title: str | None = None
    skills: list[str] = Field(default_factory=list)
    total_experience_years: float | None = None
    companies: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    resume_summary: str = ""
    experience_extraction_method: Literal[
        "explicit_text",
        "job_history_dates",
        "unknown",
    ] = "unknown"
    experience_date_ranges: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1)
    parsing_status: Literal["parsed", "review_required", "failed"]
    parser_used: Literal["ollama", "rule_based"]

    @field_validator(
        "candidate_name",
        "email",
        "phone",
        "current_title",
        mode="before",
    )
    @classmethod
    def normalize_optional_string(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        cleaned_value = value.strip()
        return cleaned_value or None

    @field_validator("resume_summary", mode="before")
    @classmethod
    def normalize_required_string(cls, value: object) -> str:
        if value is None:
            return ""
        if not isinstance(value, str):
            return value
        return value.strip()

    @field_validator(
        "skills",
        "companies",
        "education",
        "experience_date_ranges",
        mode="before",
    )
    @classmethod
    def normalize_string_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return value

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

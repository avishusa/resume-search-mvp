from app.parsing.base import ResumeParserProvider
from app.schemas.candidate import CandidateProfile
from app.services.candidate_profile_service import CandidateProfileService
from app.services.experience_extractor import ExperienceExtractionResult


class FakeParser:
    parser_name = "ollama"

    def __init__(self, total_experience_years: float | None = None) -> None:
        self._total_experience_years = total_experience_years

    def parse(self, resume_text: str) -> CandidateProfile:
        return CandidateProfile(
            candidate_name="Jane Candidate",
            email="jane@example.com",
            phone=None,
            current_title="AI Engineer",
            skills=["Python"],
            total_experience_years=self._total_experience_years,
            companies=[],
            education=[],
            resume_summary="",
            confidence_score=0.9,
            parsing_status="parsed",
            parser_used="ollama",
        )


class FakeExperienceExtractor:
    def __init__(self, result: ExperienceExtractionResult) -> None:
        self._result = result

    def extract(self, resume_text: str) -> ExperienceExtractionResult:
        return self._result


def _service(
    parser: ResumeParserProvider,
    extraction_result: ExperienceExtractionResult,
) -> CandidateProfileService:
    return CandidateProfileService(
        primary_parser=parser,
        fallback_parser=parser,
        experience_extractor=FakeExperienceExtractor(extraction_result),
    )


def test_explicit_experience_overrides_ollama_value() -> None:
    service = _service(
        FakeParser(total_experience_years=10),
        ExperienceExtractionResult(
            total_years=4.5,
            method="explicit_text",
            date_ranges=[],
        ),
    )

    profile = service.parse("4.5+ years of experience")

    assert profile.total_experience_years == 4.5
    assert profile.experience_extraction_method == "explicit_text"


def test_missing_ollama_experience_uses_job_history_dates() -> None:
    service = _service(
        FakeParser(total_experience_years=None),
        ExperienceExtractionResult(
            total_years=3.0,
            method="job_history_dates",
            date_ranges=["Jan 2020 - Dec 2022"],
        ),
    )

    profile = service.parse("Experience\nJan 2020 - Dec 2022")

    assert profile.total_experience_years == 3.0
    assert profile.experience_extraction_method == "job_history_dates"
    assert profile.experience_date_ranges == ["Jan 2020 - Dec 2022"]

import pytest
from pydantic import ValidationError

from app.schemas.candidate import CandidateProfile


def test_candidate_profile_normalizes_strings_and_lists() -> None:
    profile = CandidateProfile(
        candidate_name="  Jane Candidate  ",
        email="  jane@example.com  ",
        phone="",
        current_title=" AI Engineer ",
        skills=[" Python ", "python", "", "FastAPI"],
        total_experience_years=5,
        companies=[" Acme ", "acme"],
        education=["  BS Computer Science  "],
        resume_summary="  Builds AI systems.  ",
        confidence_score=0.9,
        parsing_status="parsed",
        parser_used="ollama",
    )

    assert profile.candidate_name == "Jane Candidate"
    assert profile.email == "jane@example.com"
    assert profile.phone is None
    assert profile.current_title == "AI Engineer"
    assert profile.skills == ["Python", "FastAPI"]
    assert profile.companies == ["Acme"]
    assert profile.resume_summary == "Builds AI systems."


def test_candidate_profile_rejects_invalid_confidence_score() -> None:
    with pytest.raises(ValidationError):
        CandidateProfile(
            candidate_name=None,
            email=None,
            phone=None,
            current_title=None,
            skills=[],
            total_experience_years=None,
            companies=[],
            education=[],
            resume_summary="",
            confidence_score=2,
            parsing_status="parsed",
            parser_used="ollama",
        )

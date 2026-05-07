from app.repositories.resume_repository import InMemoryResumeRepository
from app.services.resume_search_service import ResumeSearchService


def test_required_skills_are_matched_case_insensitively() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    matched_skills = service.match_skills(
        ["Python", "LangChain"],
        ["python", "LANGCHAIN"],
    )

    assert matched_skills == ["Python", "LangChain"]


def test_missing_required_skills_are_returned_correctly() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())
    required_skills = ["Python", "Docker"]

    missing_skills = [
        skill
        for skill in required_skills
        if skill not in service.match_skills(required_skills, ["Python"])
    ]

    assert missing_skills == ["Docker"]


def test_nice_to_have_skills_are_returned_separately() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    matched_skills = service.match_skills(
        ["FastAPI", "Docker"],
        ["Python", "fastapi"],
    )

    assert matched_skills == ["FastAPI"]

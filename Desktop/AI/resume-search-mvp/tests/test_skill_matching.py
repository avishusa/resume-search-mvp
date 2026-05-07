from app.repositories.resume_repository import InMemoryResumeRepository
from app.schemas.job import JobSearchRequest
from app.services.resume_search_service import ResumeSearchService


def test_required_skills_are_matched_case_insensitively() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    matched_skills = service.match_skills(
        "Built production services with python and langchain.",
        ["Python", "LangChain"],
    )

    assert matched_skills == ["Python", "LangChain"]


def test_missing_required_skills_are_returned_correctly() -> None:
    repository = InMemoryResumeRepository()
    service = ResumeSearchService(repository)
    request = JobSearchRequest(
        job_title="AI Engineer",
        job_description="Build AI systems.",
        required_skills=["Python", "Docker"],
        nice_to_have_skills=[],
    )

    missing_skills = [
        skill
        for skill in request.required_skills
        if skill not in service.match_skills("AI Engineer\nPython projects", request.required_skills)
    ]

    assert missing_skills == ["Docker"]

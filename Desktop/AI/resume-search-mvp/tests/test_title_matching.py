from app.repositories.resume_repository import InMemoryResumeRepository
from app.services.resume_search_service import ResumeSearchService


def test_ai_engineer_matches_ai_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "AI Engineer") > 0


def test_ai_engineer_does_not_match_ml_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "ML Engineer") == 0


def test_ai_engineer_does_not_match_data_scientist() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "Data Scientist") == 0


def test_software_engineer_matches_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Software Engineer", "Software Engineer") > 0


def test_ai_software_engineer_matches_ai_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Software Engineer", "AI Software Engineer") > 0


def test_ai_engineer_matches_ai_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "AI Software Engineer") > 0


def test_software_engineer_matches_ai_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Software Engineer", "AI Software Engineer") > 0


def test_ml_engineer_does_not_match_ai_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("ML Engineer", "AI Software Engineer") == 0

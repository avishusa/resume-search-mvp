from app.repositories.resume_repository import InMemoryResumeRepository
from app.services.resume_search_service import ResumeSearchService
from app.services.matching import StrictTitleMatcher


def test_ai_engineer_matches_ai_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "AI Engineer") > 0


def test_ai_engineer_matches_ai_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "AI Software Engineer") > 0


def test_software_engineer_matches_ai_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Software Engineer", "AI Software Engineer") > 0


def test_ai_software_engineer_matches_ai_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Software Engineer", "AI Software Engineer") > 0


def test_ai_engineer_does_not_match_ml_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "ML Engineer") == 0


def test_ai_engineer_does_not_match_data_scientist() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "Data Scientist") == 0


def test_ai_engineer_does_not_match_machine_learning_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "Machine Learning Engineer") == 0


def test_ml_engineer_does_not_match_ai_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("ML Engineer", "AI Software Engineer") == 0


def test_data_scientist_matches_data_scientist() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Data Scientist", "Data Scientist") > 0


def test_software_engineer_matches_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Software Engineer", "Software Engineer") > 0


def test_software_engineer_does_not_match_data_scientist() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Software Engineer", "Data Scientist") == 0


def test_data_science_matches_data_scientist() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Data Science", "Data Scientist") > 0


def test_data_scientist_matches_data_science() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Data Scientist", "Data Science") > 0


def test_senior_consultant_data_science_matches_data_science() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Data Science", "Senior Consultant Data Science") > 0


def test_data_science_does_not_match_ai_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Data Science", "AI Engineer") == 0


def test_data_science_does_not_match_software_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Data Science", "Software Engineer") == 0


def test_machine_learning_engineer_matches_data_scientist_by_family() -> None:
    match = StrictTitleMatcher().match("Machine Learning Engineer", "Data Scientist")

    assert match.score == 0.75
    assert match.match_type == "title_family"
    assert match.jd_title_family == "ml_data_science"
    assert match.candidate_title_family == "ml_data_science"


def test_machine_learning_engineer_matches_senior_data_scientist() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Machine Learning Engineer", "Senior Data Scientist") > 0


def test_ml_engineer_matches_data_scientist() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("ML Engineer", "Data Scientist") > 0


def test_data_scientist_matches_machine_learning_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Data Scientist", "Machine Learning Engineer") > 0


def test_ai_engineer_matches_ai_applications_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "AI Applications Engineer") > 0


def test_ai_engineer_matches_gen_ai_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("AI Engineer", "Gen AI Engineer") > 0


def test_machine_learning_engineer_does_not_match_frontend_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Machine Learning Engineer", "Frontend Engineer") == 0


def test_devops_engineer_does_not_match_ai_engineer() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("DevOps Engineer", "AI Engineer") == 0


def test_business_analyst_does_not_match_data_scientist() -> None:
    service = ResumeSearchService(InMemoryResumeRepository())

    assert service.title_score("Business Analyst", "Data Scientist") == 0


def test_compound_candidate_title_segments_match_ml_and_data_titles() -> None:
    matcher = StrictTitleMatcher()
    title = "Senior Data Scientist & Machine Learning Software Engineer (Generative AI) PURELOGICS"

    assert matcher.match("Data Scientist", title).score > 0
    assert matcher.match("Data Science", title).score > 0
    assert matcher.match("Machine Learning Engineer", title).score > 0


def test_title_family_match_has_lower_score_than_exact_match() -> None:
    matcher = StrictTitleMatcher()

    exact_match = matcher.match("Machine Learning Engineer", "Machine Learning Engineer")
    family_match = matcher.match("Machine Learning Engineer", "Data Scientist")

    assert exact_match.score == 1.0
    assert family_match.score == 0.75
    assert exact_match.score > family_match.score

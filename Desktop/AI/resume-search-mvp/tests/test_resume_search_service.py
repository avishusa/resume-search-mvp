from datetime import UTC, datetime

from app.repositories.resume_repository import InMemoryResumeRepository, ResumeRecord
from app.schemas.candidate import CandidateProfile
from app.schemas.job import JobSearchRequest
from app.services.resume_search_service import ResumeSearchService


def _record(
    resume_id: str,
    file_name: str,
    title: str,
    skills: list[str],
    years: float | None = None,
    extraction_status: str = "extracted",
    parsing_status: str = "parsed",
) -> ResumeRecord:
    now = datetime.now(UTC)
    return ResumeRecord(
        resume_id=resume_id,
        file_name=file_name,
        source_path=f"/fake/{file_name}",
        file_type="text/plain",
        file_hash=resume_id,
        last_modified=now,
        extraction_status=extraction_status,
        parsing_status=parsing_status,
        parser_used="ollama",
        parsing_error=None,
        ollama_error=None,
        ollama_raw_response_preview=None,
        ollama_model="llama3.1:8b",
        extracted_text="\n".join([title, " ".join(skills)]),
        parsed_at=now,
        ingested_at=now,
        candidate_profile=CandidateProfile(
            candidate_name=file_name,
            email=f"{resume_id}@example.com",
            phone=None,
            current_title=title,
            skills=skills,
            total_experience_years=years,
            companies=[],
            education=[],
            resume_summary="",
            confidence_score=0.9,
            parsing_status=parsing_status,
            parser_used="ollama",
        ),
    )


def test_exact_title_candidate_with_more_skills_ranks_above_lower_skill_candidate() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "strong.txt", "AI Engineer", ["Python", "LLM"]))
    repository.save(_record("2", "weak.txt", "AI Engineer", ["Python"]))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python", "LLM"],
            nice_to_have_skills=[],
            min_years_experience=0,
        )
    )

    assert [result.file_name for result in response.results] == ["strong.txt", "weak.txt"]


def test_candidate_with_no_title_match_is_excluded() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "ai.txt", "AI Engineer", ["Python"]))
    repository.save(_record("2", "data.txt", "Data Scientist", ["Python"]))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python"],
            nice_to_have_skills=[],
            min_years_experience=0,
        )
    )

    assert [result.file_name for result in response.results] == ["ai.txt"]


def test_candidate_with_more_required_skills_ranks_higher() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "three.txt", "AI Software Engineer", ["Python", "LLM", "LangChain"]))
    repository.save(_record("2", "one.txt", "AI Software Engineer", ["Python"]))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python", "LLM", "LangChain"],
            nice_to_have_skills=[],
            min_years_experience=0,
        )
    )

    assert response.results[0].file_name == "three.txt"
    assert response.results[0].required_skill_score > response.results[1].required_skill_score


def test_candidate_with_six_years_is_returned_for_min_five_years() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "senior.txt", "AI Engineer", ["Python"], years=6))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python"],
            nice_to_have_skills=[],
            min_years_experience=5,
        )
    )

    assert response.matched_count == 1
    assert response.results[0].file_name == "senior.txt"
    assert response.results[0].experience_score == 1.0


def test_candidate_with_four_years_is_returned_but_not_shortlisted_for_min_five_years() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "mid.txt", "AI Engineer", ["Python"], years=4))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python"],
            nice_to_have_skills=[],
            min_years_experience=5,
        )
    )

    assert response.matched_count == 1
    assert response.excluded_by_experience_count == 1
    assert response.results[0].file_name == "mid.txt"
    assert response.results[0].shortlist_decision == "not_recommended"
    assert response.results[0].recommendation_level == "weak_match"
    assert response.results[0].experience_score == 0.0
    assert response.results[0].experience_passed is False
    assert (
        response.results[0].experience_match_reason
        == "Experience requirement not met: 4 years < 5 years."
    )


def test_candidate_with_null_experience_is_returned_for_review_when_min_experience_required() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "unknown.txt", "AI Engineer", ["Python"], years=None))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python"],
            nice_to_have_skills=[],
            min_years_experience=5,
        )
    )

    assert response.matched_count == 1
    assert response.excluded_by_experience_count == 1
    assert response.results[0].shortlist_decision == "review"
    assert response.results[0].recommendation_level == "moderate_match"
    assert response.results[0].experience_passed is None
    assert (
        response.results[0].experience_match_reason
        == "Experience unknown; requirement could not be verified."
    )


def test_candidate_with_null_experience_is_allowed_when_min_experience_is_zero() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "unknown.txt", "AI Engineer", ["Python"], years=None))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python"],
            nice_to_have_skills=[],
            min_years_experience=0,
        )
    )

    assert response.matched_count == 1
    assert response.results[0].experience_score == 0.0


def test_experience_filter_happens_after_strict_title_match() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "below.txt", "AI Engineer", ["Python"], years=4))
    repository.save(_record("2", "wrong-title.txt", "Data Scientist", ["Python"], years=10))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python"],
            nice_to_have_skills=[],
            min_years_experience=5,
        )
    )

    assert response.excluded_by_title_count == 1
    assert response.excluded_by_experience_count == 1
    assert response.matched_count == 1
    assert response.results[0].file_name == "below.txt"


def test_candidate_with_no_title_match_is_excluded_even_with_high_experience() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "data.txt", "Data Scientist", ["Python"], years=10))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python"],
            nice_to_have_skills=[],
            min_years_experience=5,
        )
    )

    assert response.excluded_by_title_count == 1
    assert response.excluded_by_experience_count == 0
    assert response.matched_count == 0


def test_search_debug_includes_title_match_details() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "data.txt", "Data Scientist", ["Python"], years=6))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Data Science",
            job_description="Data role",
            required_skills=["Python"],
            nice_to_have_skills=[],
            min_years_experience=0,
            debug=True,
        )
    )

    result = response.results[0]
    assert result.normalized_jd_title == "data science"
    assert result.normalized_candidate_title == "data scientist"
    assert result.title_match_type == "alias"
    assert (
        result.title_match_reason
        == "Alias title match: Data Science and Data Scientist are configured aliases."
    )


def test_strong_match_returns_shortlist_decision() -> None:
    repository = InMemoryResumeRepository()
    repository.save(
        _record(
            "1",
            "strong.txt",
            "Data Scientist",
            ["Python", "SQL", "Machine Learning", "Docker"],
            years=4.5,
        )
    )
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Data Science",
            job_description="Data role",
            required_skills=["Python", "SQL", "Machine Learning"],
            nice_to_have_skills=["Docker", "GCP"],
            min_years_experience=3,
        )
    )

    result = response.results[0]
    assert result.recommendation_level == "strong_match"
    assert result.shortlist_decision == "shortlist"
    assert result.required_skill_match_percentage == 100
    assert result.nice_to_have_skill_match_percentage == 50
    assert result.missing_nice_to_have_skills == ["GCP"]
    assert result.title_match_type == "alias"
    assert "Strong match" in result.match_summary
    assert "Experience requirement met: 4.5 years >= 3 years" in result.match_summary


def test_moderate_match_returns_review_decision() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "moderate.txt", "AI Engineer", ["Python", "SQL"]))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python", "SQL", "LangChain"],
            nice_to_have_skills=[],
            min_years_experience=0,
        )
    )

    result = response.results[0]
    assert result.recommendation_level == "moderate_match"
    assert result.shortlist_decision == "review"
    assert result.required_skill_match_percentage == 66.7
    assert result.missing_required_skills == ["LangChain"]


def test_weak_match_returns_not_recommended_decision() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "weak.txt", "AI Engineer", ["Python"]))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python", "SQL", "LangChain"],
            nice_to_have_skills=[],
            min_years_experience=0,
        )
    )

    result = response.results[0]
    assert result.recommendation_level == "weak_match"
    assert result.shortlist_decision == "not_recommended"
    assert result.required_skill_match_percentage == 33.3
    assert "Missing required skills: SQL, LangChain" in result.required_skill_match_reason


def test_match_summary_contains_title_experience_and_skill_explanation() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "summary.txt", "AI Software Engineer", ["Python"], years=6))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="AI Engineer",
            job_description="AI role",
            required_skills=["Python"],
            nice_to_have_skills=["Docker"],
            min_years_experience=5,
        )
    )

    result = response.results[0]
    assert result.title_match_type == "compound"
    assert "Compound title match: AI Engineer matched AI Software Engineer" in result.match_summary
    assert "Experience requirement met: 6 years >= 5 years" in result.match_summary
    assert "Matched 1/1 required skills: Python" in result.match_summary
    assert result.missing_nice_to_have_skills == ["Docker"]
    assert "Missing optional nice-to-have skills: Docker" in result.match_summary


def test_missing_nice_to_have_skills_do_not_block_shortlist() -> None:
    repository = InMemoryResumeRepository()
    repository.save(
        _record(
            "1",
            "required-only.txt",
            "Data Scientist",
            ["Python", "SQL", "Machine Learning"],
            years=4.5,
        )
    )
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Data Scientist",
            job_description="Data role",
            required_skills=["Python", "SQL", "Machine Learning"],
            nice_to_have_skills=["GCP", "Docker", "FastAPI"],
            min_years_experience=3,
        )
    )

    result = response.results[0]
    assert result.shortlist_decision == "shortlist"
    assert result.recommendation_level == "strong_match"
    assert result.matched_nice_to_have_skills == []
    assert result.missing_nice_to_have_skills == ["GCP", "Docker", "FastAPI"]
    assert result.final_exclusion_reason is None
    assert "Missing optional nice-to-have skills: GCP, Docker, FastAPI" in result.match_summary


def test_nice_to_have_skills_only_add_small_score_bonus() -> None:
    repository = InMemoryResumeRepository()
    repository.save(
        _record(
            "1",
            "bonus.txt",
            "Data Scientist",
            ["Python", "SQL", "Machine Learning", "GCP", "Docker", "FastAPI"],
            years=4.5,
        )
    )
    repository.save(
        _record(
            "2",
            "no-bonus.txt",
            "Data Scientist",
            ["Python", "SQL", "Machine Learning"],
            years=4.5,
        )
    )
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Data Scientist",
            job_description="Data role",
            required_skills=["Python", "SQL", "Machine Learning"],
            nice_to_have_skills=["GCP", "Docker", "FastAPI"],
            min_years_experience=3,
        )
    )

    bonus_result = response.results[0]
    no_bonus_result = response.results[1]
    assert bonus_result.shortlist_decision == "shortlist"
    assert no_bonus_result.shortlist_decision == "shortlist"
    assert bonus_result.overall_score > no_bonus_result.overall_score
    assert round(bonus_result.overall_score - no_bonus_result.overall_score, 4) == 0.05


def test_nice_to_have_matches_do_not_override_missing_required_skills() -> None:
    repository = InMemoryResumeRepository()
    repository.save(
        _record(
            "1",
            "optional-only.txt",
            "Data Scientist",
            ["Python", "GCP", "Docker", "FastAPI"],
            years=4.5,
        )
    )
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Data Scientist",
            job_description="Data role",
            required_skills=["Python", "SQL", "Machine Learning"],
            nice_to_have_skills=["GCP", "Docker", "FastAPI"],
            min_years_experience=3,
        )
    )

    result = response.results[0]
    assert result.required_skill_score == 0.3333
    assert result.nice_to_have_skill_score == 1.0
    assert result.shortlist_decision == "not_recommended"
    assert result.recommendation_level == "weak_match"
    assert result.final_exclusion_reason is None


def test_data_scientist_below_experience_still_appears_in_all_results() -> None:
    repository = InMemoryResumeRepository()
    repository.save(
        _record(
            "bhavesh",
            "bhavesh.pdf",
            "Data Scientist",
            ["Python", "SQL", "Machine Learning"],
            years=4.5,
        )
    )
    repository.save(
        _record(
            "jillani",
            "jillani.pdf",
            "Senior Data Scientist",
            ["Python", "SQL", "Machine Learning"],
            years=5.4,
        )
    )
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Data Scientist",
            job_description="Data science role",
            required_skills=["Python", "SQL", "Machine Learning"],
            nice_to_have_skills=[],
            min_years_experience=5,
        )
    )

    assert response.matched_count == 2
    assert response.excluded_by_experience_count == 1
    assert [result.file_name for result in response.results] == [
        "jillani.pdf",
        "bhavesh.pdf",
    ]
    assert response.results[0].shortlist_decision == "shortlist"
    assert response.results[0].experience_passed is True
    assert response.results[1].shortlist_decision == "not_recommended"
    assert response.results[1].experience_passed is False
    assert (
        response.results[1].experience_match_reason
        == "Experience requirement not met: 4.5 years < 5 years."
    )


def test_debug_response_lists_candidates_excluded_by_title() -> None:
    repository = InMemoryResumeRepository()
    repository.save(_record("1", "data.txt", "Data Scientist", ["Python"], years=6))
    repository.save(_record("2", "wrong.txt", "AI Engineer", ["Python"], years=6))
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Data Scientist",
            job_description="Data role",
            required_skills=["Python"],
            nice_to_have_skills=[],
            min_years_experience=0,
            debug=True,
        )
    )

    assert response.matched_count == 1
    assert len(response.debug_excluded_by_title) == 1
    assert response.debug_excluded_by_title[0].file_name == "wrong.txt"
    assert (
        response.debug_excluded_by_title[0].final_exclusion_reason
        == "Excluded because strict title matching failed."
    )


def test_machine_learning_engineer_search_returns_data_scientist_candidate() -> None:
    repository = InMemoryResumeRepository()
    repository.save(
        _record(
            "1",
            "data-scientist.txt",
            "Data Scientist",
            ["Python", "Machine Learning"],
            years=5,
        )
    )
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Machine Learning Engineer",
            job_description="ML role",
            required_skills=["Python", "Machine Learning"],
            nice_to_have_skills=[],
            min_years_experience=0,
        )
    )

    assert response.matched_count == 1
    assert response.results[0].file_name == "data-scientist.txt"
    assert response.results[0].title_match_type == "title_family"
    assert response.results[0].title_score == 0.75


def test_data_scientist_search_returns_machine_learning_engineer_candidate() -> None:
    repository = InMemoryResumeRepository()
    repository.save(
        _record(
            "1",
            "ml-engineer.txt",
            "Machine Learning Engineer",
            ["Python", "Machine Learning"],
            years=5,
        )
    )
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Data Scientist",
            job_description="Data science role",
            required_skills=["Python", "Machine Learning"],
            nice_to_have_skills=[],
            min_years_experience=0,
        )
    )

    assert response.matched_count == 1
    assert response.results[0].file_name == "ml-engineer.txt"
    assert response.results[0].title_match_type == "title_family"


def test_software_engineer_search_does_not_return_data_scientist_with_overlapping_skills() -> None:
    repository = InMemoryResumeRepository()
    repository.save(
        _record(
            "1",
            "data-scientist.txt",
            "Data Scientist",
            ["Python", "SQL", "Docker"],
            years=5,
        )
    )
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Software Engineer",
            job_description="Software role",
            required_skills=["Python", "SQL"],
            nice_to_have_skills=["Docker"],
            min_years_experience=0,
        )
    )

    assert response.matched_count == 0
    assert response.excluded_by_title_count == 1


def test_exact_title_match_ranks_above_title_family_match() -> None:
    repository = InMemoryResumeRepository()
    repository.save(
        _record(
            "1",
            "exact.txt",
            "Machine Learning Engineer",
            ["Python", "Machine Learning"],
            years=5,
        )
    )
    repository.save(
        _record(
            "2",
            "family.txt",
            "Data Scientist",
            ["Python", "Machine Learning"],
            years=5,
        )
    )
    service = ResumeSearchService(repository)

    response = service.search(
        JobSearchRequest(
            job_title="Machine Learning Engineer",
            job_description="ML role",
            required_skills=["Python", "Machine Learning"],
            nice_to_have_skills=[],
            min_years_experience=0,
        )
    )

    assert [result.file_name for result in response.results] == [
        "exact.txt",
        "family.txt",
    ]
    assert response.results[0].title_match_type == "exact"
    assert response.results[1].title_match_type == "title_family"

from app.parsing.text_cleaning import (
    build_resume_digest_for_llm,
    clean_resume_text_for_llm,
)


def test_clean_resume_text_for_llm_removes_private_use_and_control_characters() -> None:
    cleaned = clean_resume_text_for_llm(
        "Bhavesh Wadhwani\n    \x00\x08 ￾ Data Scientist"
    )

    assert "" not in cleaned
    assert "" not in cleaned
    assert "" not in cleaned
    assert "￾" not in cleaned
    assert "\x00" not in cleaned
    assert "Bhavesh Wadhwani" in cleaned
    assert "Data Scientist" in cleaned


def test_clean_resume_text_for_llm_preserves_resume_content() -> None:
    cleaned = clean_resume_text_for_llm(
        "Bhavesh Wadhwani\n"
        "DATA SCIENTIST · GOOGLE CLOUD CERTIFIED\n"
        "Email: bhavesh@example.com\n"
        "Phone: +1 312-555-1212\n"
        "Skills: Python, SQL/MS-SQL, Machine Learning, GCP, Docker\n"
    )

    assert "Bhavesh Wadhwani" in cleaned
    assert "bhavesh@example.com" in cleaned
    assert "+1 312-555-1212" in cleaned
    assert "DATA SCIENTIST" in cleaned
    assert "Python" in cleaned
    assert "Machine Learning" in cleaned


def test_resume_digest_includes_top_summary_and_title_text() -> None:
    digest = build_resume_digest_for_llm(
        "Jane Candidate\n"
        "Data Scientist\n"
        "Summary: Builds machine learning systems.\n"
        + ("Older project detail. " * 500),
        max_chars=1200,
    )

    assert "Jane Candidate" in digest
    assert "Data Scientist" in digest
    assert "Summary: Builds machine learning systems." in digest


def test_resume_digest_includes_skills_and_experience_sections() -> None:
    resume_text = (
        "Jane Candidate\n"
        "Machine Learning Engineer\n"
        + ("Long project detail. " * 300)
        + "\nTechnical Skills\nPython, SQL, Machine Learning, Docker\n"
        + "\nProfessional Experience\nAcme AI\nJan 2021 - Present\nBuilt ML services.\n"
        + "\nEducation\nBS Computer Science\n"
    )

    digest = build_resume_digest_for_llm(resume_text, max_chars=5000)

    assert "Technical Skills" in digest
    assert "Python, SQL, Machine Learning, Docker" in digest
    assert "Professional Experience" in digest
    assert "Jan 2021 - Present" in digest
    assert "Education" in digest


def test_resume_digest_respects_max_char_limit() -> None:
    digest = build_resume_digest_for_llm(
        "Jane Candidate\nData Scientist\n" + ("Details. " * 1000),
        max_chars=500,
    )

    assert len(digest) <= 500

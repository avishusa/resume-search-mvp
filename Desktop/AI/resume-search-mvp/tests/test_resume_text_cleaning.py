from app.parsing.text_cleaning import clean_resume_text_for_llm


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

from app.parsing.rule_based import RuleBasedResumeParserProvider


def test_rule_based_parser_extracts_email_phone_title_and_skills() -> None:
    parser = RuleBasedResumeParserProvider(skill_catalog=["Python", "FastAPI", "Docker"])

    profile = parser.parse(
        "AI Engineer\n"
        "jane@example.com\n"
        "(312) 555-1212\n"
        "Skills: Python, FastAPI"
    )

    assert profile.parser_used == "rule_based"
    assert profile.parsing_status == "parsed"
    assert profile.email == "jane@example.com"
    assert profile.phone == "(312) 555-1212"
    assert profile.current_title == "AI Engineer"
    assert profile.skills == ["Python", "FastAPI"]


def test_rule_based_parser_marks_review_required_when_important_fields_missing() -> None:
    parser = RuleBasedResumeParserProvider(skill_catalog=["Python"])

    profile = parser.parse("Skills: Python")

    assert profile.parser_used == "rule_based"
    assert profile.parsing_status == "review_required"


def test_rule_based_parser_extracts_bhavesh_style_resume_with_pdf_symbols() -> None:
    parser = RuleBasedResumeParserProvider(
        skill_catalog=["Python", "SQL", "MS-SQL", "Machine Learning", "GCP", "Docker"]
    )

    profile = parser.parse(
        "Bhavesh Wadhwani\n"
        "DATA SCIENTIST · GOOGLE CLOUD CERTIFIED · MICROSOFT CERTIFIED\n"
        " +1 312-555-1212   bhavesh@example.com   Chicago\n"
        "4.5+ years of work experience\n"
        "Skills: Python, SQL/MS-SQL, Machine Learning, GCP, Docker\n"
        "￾"
    )

    assert profile.parser_used == "rule_based"
    assert profile.parsing_status == "parsed"
    assert profile.candidate_name == "Bhavesh Wadhwani"
    assert profile.current_title == "Data Scientist"
    assert profile.email == "bhavesh@example.com"
    assert profile.phone == "+1 312-555-1212"
    assert profile.total_experience_years == 4.5
    assert "Python" in profile.skills
    assert "Machine Learning" in profile.skills
    assert "GCP" in profile.skills
    assert "Docker" in profile.skills


def test_rule_based_parser_extracts_jillani_style_compound_title() -> None:
    parser = RuleBasedResumeParserProvider(skill_catalog=["Python", "Machine Learning"])

    profile = parser.parse(
        "Muhammad G. Jillani\n"
        "Senior Data Scientist and Machine Learning Engineer\n"
        "m.g.jillani123@gmail.com\n"
        "Skills: Python, Machine Learning\n"
    )

    assert profile.parser_used == "rule_based"
    assert profile.parsing_status == "parsed"
    assert profile.candidate_name == "Muhammad G. Jillani"
    assert profile.current_title == "Senior Data Scientist and Machine Learning Engineer"
    assert profile.email == "m.g.jillani123@gmail.com"


def test_rule_based_parser_extracts_jillani_ampersand_title() -> None:
    parser = RuleBasedResumeParserProvider(skill_catalog=["Python", "Machine Learning"])

    profile = parser.parse(
        "Muhammad G. Jillani\n"
        "Senior Data Scientist & Machine Learning Software Engineer (Generative AI) PURELOGICS\n"
        "m.g.jillani123@gmail.com\n"
        "Skills: Python, Machine Learning\n"
    )

    assert profile.parser_used == "rule_based"
    assert profile.parsing_status == "parsed"
    assert profile.current_title == "Senior Data Scientist & Machine Learning Software Engineer"

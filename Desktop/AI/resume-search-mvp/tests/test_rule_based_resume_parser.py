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

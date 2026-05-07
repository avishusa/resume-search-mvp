from datetime import date

from app.services.experience_extractor import ExperienceExtractor


def test_jan_2021_present_calculates_with_fixed_current_date() -> None:
    extractor = ExperienceExtractor()

    result = extractor.extract(
        "Experience\nAI Engineer\nJan 2021 - Present",
        current_date=date(2024, 12, 15),
    )

    assert result.method == "job_history_dates"
    assert result.total_years == 4.0
    assert result.date_ranges == ["Jan 2021 - Present"]


def test_jun_2019_dec_2020_calculates_correctly() -> None:
    extractor = ExperienceExtractor()

    result = extractor.extract(
        "Work Experience\nSoftware Engineer\nJun 2019 - Dec 2020",
        current_date=date(2024, 1, 1),
    )

    assert result.total_years == 1.6


def test_numeric_month_range_calculates_correctly() -> None:
    extractor = ExperienceExtractor()

    result = extractor.extract(
        "Professional Experience\nBackend Engineer\n06/2019 - 12/2020",
        current_date=date(2024, 1, 1),
    )

    assert result.total_years == 1.6


def test_year_only_range_uses_full_years() -> None:
    extractor = ExperienceExtractor()

    result = extractor.extract(
        "Employment History\nData Engineer\n2019 - 2022",
        current_date=date(2024, 1, 1),
    )

    assert result.total_years == 4.0


def test_overlapping_ranges_are_not_double_counted() -> None:
    extractor = ExperienceExtractor()

    result = extractor.extract(
        "Career History\n"
        "AI Engineer\nJan 2020 - Dec 2022\n"
        "Software Engineer\nJan 2021 - Dec 2023",
        current_date=date(2024, 1, 1),
    )

    assert result.total_years == 4.0


def test_education_dates_are_ignored() -> None:
    extractor = ExperienceExtractor()

    result = extractor.extract(
        "Education\nBS Computer Science\n2019 - 2022",
        current_date=date(2024, 1, 1),
    )

    assert result.total_years is None
    assert result.method == "unknown"


def test_project_dates_are_ignored() -> None:
    extractor = ExperienceExtractor()

    result = extractor.extract(
        "Projects\nResume Search MVP\nJan 2021 - Present",
        current_date=date(2024, 12, 15),
    )

    assert result.total_years is None
    assert result.method == "unknown"


def test_explicit_experience_takes_priority_over_calculated_dates() -> None:
    extractor = ExperienceExtractor()

    result = extractor.extract(
        "4.5+ years of experience\n"
        "Experience\nAI Engineer\nJan 2020 - Dec 2023",
        current_date=date(2024, 1, 1),
    )

    assert result.total_years == 4.5
    assert result.method == "explicit_text"
    assert result.date_ranges == []

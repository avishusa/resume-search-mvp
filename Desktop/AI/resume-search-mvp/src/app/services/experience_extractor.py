import re
from dataclasses import dataclass
from datetime import date


EXPERIENCE_HEADINGS = {
    "experience",
    "work experience",
    "professional experience",
    "employment history",
    "career history",
}

NON_EXPERIENCE_HEADINGS = {
    "professional summary",
    "summary",
    "education",
    "projects",
    "project experience",
    "certifications",
    "certification",
    "publications",
    "skills",
    "technical skills",
}

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

PRESENT_WORDS = {"present", "current", "now", "till date"}
DATE_PATTERN = (
    r"(?:"
    r"(?:Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|"
    r"Aug|August|Sep|Sept|September|Oct|October|Nov|November|Dec|December)"
    r"\s+\d{4}"
    r"|\d{1,2}/\d{4}"
    r"|\d{4}"
    r")"
)
END_DATE_PATTERN = f"(?:{DATE_PATTERN}|Present|Current|Now|Till Date)"
DATE_RANGE_RE = re.compile(
    rf"(?P<start>{DATE_PATTERN})\s*(?:-|–|—|\bto\b)\s*(?P<end>{END_DATE_PATTERN})",
    re.IGNORECASE,
)
EXPLICIT_EXPERIENCE_RE = re.compile(
    r"(?P<years>\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s+(?:of\s+)?experience",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MonthRange:
    start_year: int
    start_month: int
    end_year: int
    end_month: int
    raw_text: str


@dataclass(frozen=True)
class ExperienceExtractionResult:
    total_years: float | None
    method: str
    date_ranges: list[str]


class ExperienceExtractor:
    def extract(
        self,
        resume_text: str,
        current_date: date | None = None,
    ) -> ExperienceExtractionResult:
        explicit_years = self.extract_explicit_years(resume_text)
        if explicit_years is not None:
            return ExperienceExtractionResult(
                total_years=explicit_years,
                method="explicit_text",
                date_ranges=[],
            )

        ranges = self.extract_job_history_ranges(resume_text, current_date or date.today())
        if not ranges:
            return ExperienceExtractionResult(
                total_years=None,
                method="unknown",
                date_ranges=[],
            )

        return ExperienceExtractionResult(
            total_years=self.calculate_unique_years(ranges),
            method="job_history_dates",
            date_ranges=[month_range.raw_text for month_range in ranges],
        )

    def extract_explicit_years(self, resume_text: str) -> float | None:
        match = EXPLICIT_EXPERIENCE_RE.search(resume_text)
        if not match:
            return None
        return float(match.group("years"))

    def extract_job_history_ranges(
        self,
        resume_text: str,
        current_date: date,
    ) -> list[MonthRange]:
        experience_text = "\n".join(self._experience_section_lines(resume_text))
        ranges: list[MonthRange] = []
        for match in DATE_RANGE_RE.finditer(experience_text):
            month_range = self._parse_range(match.group(0), current_date)
            if month_range is not None:
                ranges.append(month_range)
        return ranges

    def calculate_unique_years(self, ranges: list[MonthRange]) -> float:
        months: set[tuple[int, int]] = set()
        for month_range in ranges:
            current_year = month_range.start_year
            current_month = month_range.start_month
            while (current_year, current_month) <= (
                month_range.end_year,
                month_range.end_month,
            ):
                months.add((current_year, current_month))
                current_month += 1
                if current_month == 13:
                    current_month = 1
                    current_year += 1
        return round(len(months) / 12, 1)

    def _experience_section_lines(self, resume_text: str) -> list[str]:
        lines: list[str] = []
        in_experience_section = False
        for raw_line in resume_text.splitlines():
            line = raw_line.strip()
            normalized_line = self._normalize_heading(line)
            if not normalized_line and in_experience_section:
                lines.append(line)
                continue
            if not normalized_line:
                continue
            if normalized_line in EXPERIENCE_HEADINGS:
                in_experience_section = True
                continue
            if normalized_line in NON_EXPERIENCE_HEADINGS:
                in_experience_section = False
                continue
            if in_experience_section:
                lines.append(line)
        return lines

    def _parse_range(
        self,
        raw_range: str,
        current_date: date,
    ) -> MonthRange | None:
        match = DATE_RANGE_RE.search(raw_range)
        if not match:
            return None
        start = self._parse_date(match.group("start"), is_start=True, current_date=current_date)
        end = self._parse_date(match.group("end"), is_start=False, current_date=current_date)
        if start is None or end is None or start > end:
            return None
        return MonthRange(
            start_year=start[0],
            start_month=start[1],
            end_year=end[0],
            end_month=end[1],
            raw_text=" ".join(raw_range.split()),
        )

    def _parse_date(
        self,
        raw_date: str,
        is_start: bool,
        current_date: date,
    ) -> tuple[int, int] | None:
        normalized_date = " ".join(raw_date.lower().strip().split())
        if normalized_date in PRESENT_WORDS:
            return current_date.year, current_date.month

        numeric_match = re.fullmatch(r"(?P<month>\d{1,2})/(?P<year>\d{4})", normalized_date)
        if numeric_match:
            month = int(numeric_match.group("month"))
            if not 1 <= month <= 12:
                return None
            return int(numeric_match.group("year")), month

        month_name_match = re.fullmatch(
            r"(?P<month>[a-z]+)\s+(?P<year>\d{4})",
            normalized_date,
        )
        if month_name_match:
            month = MONTHS.get(month_name_match.group("month"))
            if month is None:
                return None
            return int(month_name_match.group("year")), month

        year_match = re.fullmatch(r"\d{4}", normalized_date)
        if year_match:
            return int(normalized_date), 1 if is_start else 12

        return None

    def _normalize_heading(self, heading: str) -> str:
        cleaned_heading = re.sub(r"[^a-zA-Z\s]", " ", heading.lower())
        return " ".join(cleaned_heading.split())

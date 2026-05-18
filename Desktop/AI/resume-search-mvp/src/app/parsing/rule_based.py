import re

from app.parsing.text_cleaning import clean_resume_text_for_llm
from app.schemas.candidate import CandidateProfile


TITLE_WORDS = {
    "ai",
    "backend",
    "data",
    "developer",
    "engineer",
    "gen",
    "learning",
    "machine",
    "python",
    "senior",
    "scientist",
    "software",
}

KNOWN_TITLE_PHRASES = [
    "Senior Data Scientist and Machine Learning Engineer",
    "Senior Data Scientist & Machine Learning Software Engineer",
    "Senior Data Scientist",
    "AI Software Engineer",
    "Machine Learning Engineer",
    "Backend Software Engineer",
    "Software Engineer",
    "Data Scientist",
    "Data Engineer",
    "AI Engineer",
    "Gen AI Engineer",
    "Python Developer",
]


class RuleBasedResumeParserProvider:
    parser_name = "rule_based"

    def __init__(self, skill_catalog: list[str] | None = None) -> None:
        self._skill_catalog = skill_catalog or [
            "Python",
            "FastAPI",
            "Docker",
            "LLM",
            "LangChain",
            "SQL",
            "PostgreSQL",
            "AWS",
            "Azure",
            "GCP",
            "Machine Learning",
            "Data Engineering",
            "JavaScript",
            "TypeScript",
            "React",
        ]

    def parse(self, resume_text: str) -> CandidateProfile:
        cleaned_resume_text = clean_resume_text_for_llm(resume_text)
        email = self._extract_email(cleaned_resume_text)
        phone = self._extract_phone(cleaned_resume_text)
        current_title = self._extract_current_title(cleaned_resume_text)
        candidate_name = self._extract_candidate_name(cleaned_resume_text)
        skills = self._extract_skills(cleaned_resume_text)
        total_experience_years = self._extract_total_experience_years(
            cleaned_resume_text
        )
        parsing_status = (
            "parsed"
            if current_title and (candidate_name or email) and (email or phone or skills)
            else "review_required"
        )

        return CandidateProfile(
            candidate_name=candidate_name,
            email=email,
            phone=phone,
            current_title=current_title,
            skills=skills,
            total_experience_years=total_experience_years,
            companies=[],
            education=[],
            resume_summary=self._build_summary(current_title, skills),
            confidence_score=self._calculate_confidence_score(
                candidate_name=candidate_name,
                email=email,
                phone=phone,
                current_title=current_title,
                skills=skills,
                total_experience_years=total_experience_years,
            ),
            parsing_status=parsing_status,
            parser_used="rule_based",
        )

    def _extract_candidate_name(self, resume_text: str) -> str | None:
        for raw_line in resume_text.splitlines()[:10]:
            line = raw_line.strip()
            if not line or len(line) > 60:
                continue
            if self._extract_email(line) or self._extract_phone(line):
                continue
            if self._line_contains_known_title(line):
                return None
            if any(
                keyword in line.lower()
                for keyword in ["resume", "curriculum", "skills", "experience"]
            ):
                continue

            words = re.findall(r"[A-Za-z][A-Za-z.'-]*", line)
            if 2 <= len(words) <= 4 and len(" ".join(words)) >= 5:
                return " ".join(words)

        return None

    def _extract_email(self, resume_text: str) -> str | None:
        match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", resume_text)
        return match.group(0) if match else None

    def _extract_phone(self, resume_text: str) -> str | None:
        match = re.search(
            r"(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}",
            resume_text,
        )
        return match.group(0) if match else None

    def _extract_skills(self, resume_text: str) -> list[str]:
        normalized_text = resume_text.lower()
        return [
            skill
            for skill in self._skill_catalog
            if re.search(rf"\b{re.escape(skill.lower())}\b", normalized_text)
        ]

    def _extract_total_experience_years(self, resume_text: str) -> float | None:
        match = re.search(
            r"(?P<years>\d+(?:\.\d+)?)\+?\s*(?:years|yrs)\s+of\s+(?:work\s+|professional\s+)?experience",
            resume_text,
            flags=re.IGNORECASE,
        )
        return float(match.group("years")) if match else None

    def _extract_current_title(self, resume_text: str) -> str | None:
        for raw_line in resume_text.splitlines()[:20]:
            line = raw_line.strip()
            if not line:
                continue

            known_title = self._extract_known_title_from_line(line)
            if known_title:
                return known_title

            if len(line) > 80:
                continue

            normalized_words = re.sub(r"[^a-zA-Z0-9\s]", " ", line.lower()).split()
            if not normalized_words:
                continue

            has_role_word = any(
                word in {"engineer", "developer", "scientist"} for word in normalized_words
            )
            uses_known_title_words = all(word in TITLE_WORDS for word in normalized_words)
            if has_role_word and uses_known_title_words:
                return line

        return None

    def _extract_known_title_from_line(self, line: str) -> str | None:
        normalized_line = re.sub(r"[^a-zA-Z0-9\s]", " ", line.lower())
        normalized_line = re.sub(r"\s+", " ", normalized_line).strip()
        for title in KNOWN_TITLE_PHRASES:
            normalized_title = re.sub(r"[^a-zA-Z0-9\s]", " ", title.lower())
            normalized_title = re.sub(r"\s+", " ", normalized_title).strip()
            if re.search(rf"\b{re.escape(normalized_title)}\b", normalized_line):
                return title
        return None

    def _line_contains_known_title(self, line: str) -> bool:
        return self._extract_known_title_from_line(line) is not None

    def _calculate_confidence_score(
        self,
        candidate_name: str | None,
        email: str | None,
        phone: str | None,
        current_title: str | None,
        skills: list[str],
        total_experience_years: float | None,
    ) -> float:
        score = 0.15
        if candidate_name:
            score += 0.15
        if email:
            score += 0.15
        if phone:
            score += 0.1
        if current_title:
            score += 0.2
        if skills:
            score += 0.15
        if total_experience_years is not None:
            score += 0.1
        return min(score, 0.85)

    def _build_summary(self, current_title: str | None, skills: list[str]) -> str:
        if current_title and skills:
            return f"{current_title} with explicit resume mentions of {', '.join(skills)}."
        if current_title:
            return f"{current_title} found in resume text."
        if skills:
            return f"Resume includes explicit mentions of {', '.join(skills)}."
        return ""

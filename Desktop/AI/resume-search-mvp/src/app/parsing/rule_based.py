import re

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
    "software",
}


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
        email = self._extract_email(resume_text)
        phone = self._extract_phone(resume_text)
        current_title = self._extract_current_title(resume_text)
        skills = self._extract_skills(resume_text)
        parsing_status = "parsed" if email and current_title else "review_required"

        return CandidateProfile(
            candidate_name=None,
            email=email,
            phone=phone,
            current_title=current_title,
            skills=skills,
            total_experience_years=None,
            companies=[],
            education=[],
            resume_summary=self._build_summary(current_title, skills),
            confidence_score=0.45 if parsing_status == "parsed" else 0.25,
            parsing_status=parsing_status,
            parser_used="rule_based",
        )

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

    def _extract_current_title(self, resume_text: str) -> str | None:
        for raw_line in resume_text.splitlines()[:20]:
            line = raw_line.strip()
            if not line or len(line) > 80:
                continue

            normalized_words = re.sub(r"[^a-zA-Z0-9\s]", " ", line.lower()).split()
            if not normalized_words:
                continue

            has_role_word = any(
                word in {"engineer", "developer"} for word in normalized_words
            )
            uses_known_title_words = all(word in TITLE_WORDS for word in normalized_words)
            if has_role_word and uses_known_title_words:
                return line

        return None

    def _build_summary(self, current_title: str | None, skills: list[str]) -> str:
        if current_title and skills:
            return f"{current_title} with explicit resume mentions of {', '.join(skills)}."
        if current_title:
            return f"{current_title} found in resume text."
        if skills:
            return f"Resume includes explicit mentions of {', '.join(skills)}."
        return ""

import re
from dataclasses import dataclass


TITLE_ALIAS_GROUPS = [
    {"data science", "data scientist"},
    {"machine learning engineer", "ml engineer"},
    {"ai engineer", "artificial intelligence engineer"},
    {"gen ai engineer", "generative ai engineer"},
    {"software engineer", "software developer"},
    {"site reliability engineer", "sre"},
]


TITLE_FAMILIES = {
    "ml_data_science": {
        "data scientist",
        "senior data scientist",
        "data science",
        "data science consultant",
        "senior consultant data science",
        "machine learning engineer",
        "ml engineer",
        "applied scientist",
        "applied machine learning engineer",
        "ai ml engineer",
        "machine learning scientist",
        "research scientist machine learning",
        "nlp engineer",
        "computer vision engineer",
    },
    "ai_genai": {
        "ai engineer",
        "artificial intelligence engineer",
        "gen ai engineer",
        "generative ai engineer",
        "ai applications engineer",
        "ai software engineer",
        "llm engineer",
        "prompt engineer",
        "ai agent engineer",
        "rag engineer",
        "conversational ai engineer",
        "ai ml engineer",
    },
    "software_engineering": {
        "software engineer",
        "software developer",
        "backend engineer",
        "backend software engineer",
        "frontend engineer",
        "frontend software engineer",
        "full stack engineer",
        "full stack software engineer",
        "python developer",
        "java developer",
        "web developer",
    },
    "data_engineering": {
        "data engineer",
        "big data engineer",
        "analytics engineer",
        "bi developer",
        "business intelligence developer",
        "etl developer",
        "data warehouse engineer",
    },
    "devops_cloud": {
        "devops engineer",
        "cloud engineer",
        "site reliability engineer",
        "sre",
        "platform engineer",
        "infrastructure engineer",
    },
}

AI_ML_CROSS_FAMILY_TERMS = {
    "ai ml engineer",
    "machine learning",
    "ml",
    "data science",
    "data scientist",
    "applied scientist",
}

FAMILY_LABELS = {
    "ml_data_science": "ML/Data Science",
    "ai_genai": "AI/GenAI",
    "software_engineering": "Software Engineering",
    "data_engineering": "Data Engineering",
    "devops_cloud": "DevOps/Cloud",
}


def normalize_title(title: str) -> str:
    cleaned_title = re.sub(r"[^a-zA-Z0-9\s]", " ", title.lower())
    return " ".join(cleaned_title.split())


def tokenize_title(title: str) -> list[str]:
    return normalize_title(title).split()


def is_ordered_subset(needle: list[str], haystack: list[str]) -> bool:
    if len(needle) > len(haystack):
        return False

    position = 0
    for word in haystack:
        if position < len(needle) and needle[position] == word:
            position += 1

    return position == len(needle)


def title_contains_phrase(title: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", title) is not None


@dataclass(frozen=True)
class TitleMatchResult:
    score: float
    normalized_jd_title: str
    normalized_candidate_title: str
    match_type: str
    reason: str
    jd_title_family: str | None = None
    candidate_title_family: str | None = None


class StrictTitleMatcher:
    def match(self, job_title: str, resume_title: str | None) -> TitleMatchResult:
        normalized_job_title = normalize_title(job_title)
        normalized_resume_title = normalize_title(resume_title or "")
        job_tokens = normalized_job_title.split()
        resume_tokens = normalized_resume_title.split()

        if not job_tokens or not resume_tokens:
            return TitleMatchResult(
                score=0,
                normalized_jd_title=normalized_job_title,
                normalized_candidate_title=normalized_resume_title,
                match_type="no_match",
                reason="One or both titles are missing.",
            )

        jd_family = self._primary_family(normalized_job_title)
        candidate_family = self._primary_family(normalized_resume_title)

        if job_tokens == resume_tokens:
            return TitleMatchResult(
                score=1.0,
                normalized_jd_title=normalized_job_title,
                normalized_candidate_title=normalized_resume_title,
                match_type="exact",
                reason=f"Exact title match: {job_title.strip()}.",
                jd_title_family=jd_family,
                candidate_title_family=candidate_family,
            )

        if self._same_alias_group(normalized_job_title, normalized_resume_title):
            return TitleMatchResult(
                score=0.95,
                normalized_jd_title=normalized_job_title,
                normalized_candidate_title=normalized_resume_title,
                match_type="alias",
                reason=(
                    "Alias title match: "
                    f"{job_title.strip()} and {resume_title.strip() if resume_title else ''} "
                    "are configured aliases."
                ),
                jd_title_family=jd_family,
                candidate_title_family=candidate_family,
            )

        if self._compound_match(normalized_job_title, normalized_resume_title):
            return TitleMatchResult(
                score=0.85,
                normalized_jd_title=normalized_job_title,
                normalized_candidate_title=normalized_resume_title,
                match_type="compound",
                reason=(
                    "Compound title match: "
                    f"{job_title.strip()} matched {resume_title.strip() if resume_title else ''}."
                ),
                jd_title_family=jd_family,
                candidate_title_family=candidate_family,
            )

        family_match = self._family_match(
            normalized_job_title,
            normalized_resume_title,
        )
        if family_match is not None:
            jd_family, candidate_family = family_match
            return TitleMatchResult(
                score=0.75,
                normalized_jd_title=normalized_job_title,
                normalized_candidate_title=normalized_resume_title,
                match_type="title_family",
                reason=self._family_match_reason(
                    job_title=job_title,
                    resume_title=resume_title or "",
                    jd_family=jd_family,
                    candidate_family=candidate_family,
                ),
                jd_title_family=jd_family,
                candidate_title_family=candidate_family,
            )

        return TitleMatchResult(
            score=0,
            normalized_jd_title=normalized_job_title,
            normalized_candidate_title=normalized_resume_title,
            match_type="no_match",
            reason="No exact, alias, compound, or controlled title-family match.",
            jd_title_family=jd_family,
            candidate_title_family=candidate_family,
        )

    def score(self, job_title: str, resume_title: str | None) -> float:
        return self.match(job_title, resume_title).score

    def _same_alias_group(
        self,
        normalized_job_title: str,
        normalized_resume_title: str,
    ) -> bool:
        for alias_group in TITLE_ALIAS_GROUPS:
            if (
                normalized_job_title in alias_group
                and normalized_resume_title in alias_group
            ):
                return True
        return False

    def _compound_match(
        self,
        normalized_job_title: str,
        normalized_resume_title: str,
    ) -> bool:
        job_tokens = normalized_job_title.split()
        resume_tokens = normalized_resume_title.split()
        if len(job_tokens) <= 1:
            return False
        if is_ordered_subset(job_tokens, resume_tokens):
            return True
        return any(
            is_ordered_subset(job_tokens, segment.split())
            for segment in self._candidate_title_segments(normalized_resume_title)
        )

    def _family_match(
        self,
        normalized_job_title: str,
        normalized_resume_title: str,
    ) -> tuple[str, str] | None:
        jd_families = self._families_for_title(normalized_job_title)
        candidate_families = self._families_for_title(normalized_resume_title)
        shared_families = jd_families & candidate_families
        if shared_families:
            family = sorted(shared_families)[0]
            return family, family

        if (
            self._ai_ml_cross_family_allowed(normalized_job_title)
            and self._ai_ml_cross_family_allowed(normalized_resume_title)
            and {"ai_genai", "ml_data_science"} <= (jd_families | candidate_families)
        ):
            jd_family = "ai_genai" if "ai_genai" in jd_families else "ml_data_science"
            candidate_family = (
                "ai_genai" if "ai_genai" in candidate_families else "ml_data_science"
            )
            return jd_family, candidate_family

        return None

    def _primary_family(self, normalized_title: str) -> str | None:
        families = self._families_for_title(normalized_title)
        return sorted(families)[0] if families else None

    def _families_for_title(self, normalized_title: str) -> set[str]:
        families: set[str] = set()
        segments = [normalized_title, *self._candidate_title_segments(normalized_title)]
        for family_name, family_titles in TITLE_FAMILIES.items():
            if any(
                self._title_matches_family_title(segment, family_title)
                for segment in segments
                for family_title in family_titles
            ):
                families.add(family_name)
        return families

    def _title_matches_family_title(self, title: str, family_title: str) -> bool:
        if title == family_title:
            return True
        if title_contains_phrase(title, family_title):
            return True
        return False

    def _candidate_title_segments(self, normalized_title: str) -> list[str]:
        raw_segments = re.split(
            r"\b(?:and|at|with)\b|&|\+|/|\(|\)|,|\||-",
            normalized_title,
        )
        segments = []
        for segment in raw_segments:
            normalized_segment = " ".join(segment.split())
            if len(normalized_segment.split()) >= 2:
                segments.append(normalized_segment)
        return segments

    def _ai_ml_cross_family_allowed(self, normalized_job_title: str) -> bool:
        return any(
            title_contains_phrase(normalized_job_title, term)
            for term in AI_ML_CROSS_FAMILY_TERMS
        )

    def _family_match_reason(
        self,
        job_title: str,
        resume_title: str,
        jd_family: str,
        candidate_family: str,
    ) -> str:
        if jd_family == candidate_family:
            return (
                "Title matched by title family: "
                f"{job_title.strip()} and {resume_title.strip()} are both in "
                f"{FAMILY_LABELS[jd_family]}."
            )

        return (
            "Title matched by related title families: "
            f"{job_title.strip()} is in {FAMILY_LABELS[jd_family]} and "
            f"{resume_title.strip()} is in {FAMILY_LABELS[candidate_family]}."
        )


class SkillMatcher:
    def match(
        self,
        requested_skills: list[str],
        parsed_resume_skills: list[str],
        extracted_text: str = "",
    ) -> list[str]:
        normalized_resume_skills = {
            skill.strip().lower() for skill in parsed_resume_skills if skill.strip()
        }
        normalized_text = extracted_text.lower()
        matched_skills: list[str] = []

        for skill in requested_skills:
            normalized_skill = skill.strip().lower()
            if not normalized_skill:
                continue
            if normalized_skill in normalized_resume_skills or normalized_skill in normalized_text:
                matched_skills.append(skill)

        return matched_skills

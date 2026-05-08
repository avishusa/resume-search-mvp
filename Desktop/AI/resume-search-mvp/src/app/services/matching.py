import re
from dataclasses import dataclass


TITLE_ALIAS_GROUPS = [
    {
        "data science",
        "data scientist",
        "senior data scientist",
        "data science consultant",
        "senior consultant data science",
    },
    {
        "ai engineer",
        "artificial intelligence engineer",
        "gen ai engineer",
        "generative ai engineer",
        "ai software engineer",
    },
    {
        "software engineer",
        "software developer",
        "ai software engineer",
    },
    {
        "machine learning engineer",
        "ml engineer",
    },
]


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


@dataclass(frozen=True)
class TitleMatchResult:
    score: float
    normalized_jd_title: str
    normalized_candidate_title: str
    match_type: str
    reason: str


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

        if job_tokens == resume_tokens:
            return TitleMatchResult(
                score=1.0,
                normalized_jd_title=normalized_job_title,
                normalized_candidate_title=normalized_resume_title,
                match_type="exact",
                reason="Normalized titles are exactly equal.",
            )

        if self._same_alias_group(normalized_job_title, normalized_resume_title):
            return TitleMatchResult(
                score=0.9,
                normalized_jd_title=normalized_job_title,
                normalized_candidate_title=normalized_resume_title,
                match_type="alias",
                reason="Titles are in the same controlled alias group.",
            )

        if len(job_tokens) > 1 and is_ordered_subset(job_tokens, resume_tokens):
            return TitleMatchResult(
                score=0.8,
                normalized_jd_title=normalized_job_title,
                normalized_candidate_title=normalized_resume_title,
                match_type="ordered_subset",
                reason="JD title tokens appear in candidate title in order.",
            )

        return TitleMatchResult(
            score=0,
            normalized_jd_title=normalized_job_title,
            normalized_candidate_title=normalized_resume_title,
            match_type="no_match",
            reason="No exact, alias, or ordered-subset title match.",
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

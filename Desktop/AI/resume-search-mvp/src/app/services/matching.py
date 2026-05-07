import re


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


class StrictTitleMatcher:
    def score(self, job_title: str, resume_title: str | None) -> float:
        if resume_title is None:
            return 0

        job_tokens = tokenize_title(job_title)
        resume_tokens = tokenize_title(resume_title)
        if not job_tokens or not resume_tokens:
            return 0

        if job_tokens == resume_tokens:
            return 1.0

        if len(job_tokens) > 1 and is_ordered_subset(job_tokens, resume_tokens):
            return 0.8

        return 0


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

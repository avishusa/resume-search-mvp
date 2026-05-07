import re

from app.repositories.resume_repository import InMemoryResumeRepository, ResumeRecord
from app.schemas.job import JobSearchRequest, JobSearchResponse, JobSearchResult


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


class ResumeSearchService:
    def __init__(self, repository: InMemoryResumeRepository) -> None:
        self._repository = repository

    def search(self, request: JobSearchRequest) -> JobSearchResponse:
        results = [
            self._score_resume(request, resume)
            for resume in self._repository.list_all()
        ]
        title_matched_results = [result for result in results if result.title_score > 0]
        ranked_results = sorted(
            title_matched_results,
            key=lambda result: (
                result.required_skill_score,
                result.nice_to_have_skill_score,
                result.overall_score,
            ),
            reverse=True,
        )
        return JobSearchResponse(results=ranked_results)

    def extract_current_title(self, resume_text: str) -> str | None:
        for raw_line in resume_text.splitlines()[:20]:
            line = raw_line.strip()
            if not line or len(line) > 80:
                continue

            normalized_words = normalize_title_words(line)
            if not normalized_words:
                continue

            has_role_word = any(word in {"engineer", "developer"} for word in normalized_words)
            uses_known_title_words = all(word in TITLE_WORDS for word in normalized_words)
            if has_role_word and uses_known_title_words:
                return line

        return None

    def title_score(self, job_title: str, resume_title: str | None) -> int:
        if resume_title is None:
            return 0

        job_words = normalize_title_words(job_title)
        resume_words = normalize_title_words(resume_title)
        if not job_words or not resume_words:
            return 0

        if job_words == resume_words:
            return 100

        if is_ordered_subset(job_words, resume_words) or is_ordered_subset(
            resume_words, job_words
        ):
            return 70

        return 0

    def match_skills(
        self,
        resume_text: str,
        skills: list[str],
    ) -> list[str]:
        normalized_text = resume_text.lower()
        return [skill for skill in skills if skill.lower() in normalized_text]

    def _score_resume(
        self,
        request: JobSearchRequest,
        resume: ResumeRecord,
    ) -> JobSearchResult:
        current_title = (
            resume.candidate_profile.current_title
            if resume.candidate_profile
            else None
        )
        title_score = self.title_score(request.job_title, current_title)
        searchable_skills_text = (
            " ".join(resume.candidate_profile.skills)
            if resume.candidate_profile
            else ""
        )
        matched_required = self.match_skills(
            searchable_skills_text,
            request.required_skills,
        )
        matched_nice = self.match_skills(
            searchable_skills_text,
            request.nice_to_have_skills,
        )
        missing_required = [
            skill for skill in request.required_skills if skill not in matched_required
        ]
        required_score = len(matched_required)
        nice_score = len(matched_nice)
        overall_score = title_score + (required_score * 10) + (nice_score * 3)

        return JobSearchResult(
            resume_id=resume.resume_id,
            file_name=resume.file_name,
            source_path=resume.source_path,
            current_title=current_title,
            title_score=title_score,
            required_skill_score=required_score,
            nice_to_have_skill_score=nice_score,
            overall_score=overall_score,
            matched_required_skills=matched_required,
            missing_required_skills=missing_required,
            matched_nice_to_have_skills=matched_nice,
            explanation=(
                f"Title score {title_score}; matched {required_score} required "
                f"skills and {nice_score} nice-to-have skills."
            ),
        )


def normalize_title_words(title: str) -> list[str]:
    cleaned_title = re.sub(r"[^a-zA-Z0-9\s]", " ", title.lower()).strip()
    return [word for word in cleaned_title.split() if word]


def is_ordered_subset(needle: list[str], haystack: list[str]) -> bool:
    if len(needle) >= len(haystack):
        return False

    position = 0
    for word in haystack:
        if position < len(needle) and needle[position] == word:
            position += 1

    return position == len(needle)

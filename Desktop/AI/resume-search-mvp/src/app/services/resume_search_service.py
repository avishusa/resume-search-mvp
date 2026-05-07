from app.repositories.resume_repository import InMemoryResumeRepository, ResumeRecord
from app.schemas.job import (
    JobSearchQuery,
    JobSearchRequest,
    JobSearchResponse,
    JobSearchResult,
)
from app.services.matching import SkillMatcher, StrictTitleMatcher


class ResumeSearchService:
    def __init__(
        self,
        repository: InMemoryResumeRepository,
        title_matcher: StrictTitleMatcher | None = None,
        skill_matcher: SkillMatcher | None = None,
    ) -> None:
        self._repository = repository
        self._title_matcher = title_matcher or StrictTitleMatcher()
        self._skill_matcher = skill_matcher or SkillMatcher()

    def search(self, request: JobSearchRequest) -> JobSearchResponse:
        candidates = [
            resume
            for resume in self._repository.list_all()
            if self._is_searchable_resume(resume)
        ]
        title_matched_resumes = [
            resume
            for resume in candidates
            if self.title_score(
                request.job_title,
                resume.candidate_profile.current_title if resume.candidate_profile else None,
            )
            > 0
        ]
        experience_matched_resumes = [
            resume
            for resume in title_matched_resumes
            if self._passes_experience_filter(
                resume.candidate_profile.total_experience_years
                if resume.candidate_profile
                else None,
                request.min_years_experience,
            )
        ]
        results = [
            self._score_resume(request, resume)
            for resume in experience_matched_resumes
        ]
        ranked_results = sorted(
            results,
            key=lambda result: (
                result.required_skill_score,
                result.nice_to_have_skill_score,
                result.experience_score,
                result.overall_score,
            ),
            reverse=True,
        )
        return JobSearchResponse(
            query=JobSearchQuery(
                job_title=request.job_title,
                required_skills=request.required_skills,
                nice_to_have_skills=request.nice_to_have_skills,
            ),
            total_candidates_considered=len(candidates),
            excluded_by_title_count=len(candidates) - len(title_matched_resumes),
            excluded_by_experience_count=len(title_matched_resumes)
            - len(experience_matched_resumes),
            matched_count=len(ranked_results),
            results=ranked_results,
        )

    def title_score(self, job_title: str, resume_title: str | None) -> float:
        return self._title_matcher.score(job_title, resume_title)

    def match_skills(
        self,
        skills: list[str],
        parsed_resume_skills: list[str] | str,
        extracted_text: str = "",
    ) -> list[str]:
        if isinstance(parsed_resume_skills, str):
            parsed_resume_skills = parsed_resume_skills.split()
        return self._skill_matcher.match(
            requested_skills=skills,
            parsed_resume_skills=parsed_resume_skills,
            extracted_text=extracted_text,
        )

    def _score_resume(
        self,
        request: JobSearchRequest,
        resume: ResumeRecord,
    ) -> JobSearchResult:
        profile = resume.candidate_profile
        current_title = profile.current_title if profile else None
        parsed_skills = profile.skills if profile else []
        title_score = self.title_score(request.job_title, current_title)
        matched_required = self.match_skills(
            request.required_skills,
            parsed_skills,
            resume.extracted_text,
        )
        matched_nice = self.match_skills(
            request.nice_to_have_skills,
            parsed_skills,
            resume.extracted_text,
        )
        missing_required = [
            skill for skill in request.required_skills if skill not in matched_required
        ]
        required_score = self._skill_score(matched_required, request.required_skills)
        nice_score = self._skill_score(matched_nice, request.nice_to_have_skills)
        experience_score = self._experience_score(
            profile.total_experience_years if profile else None,
            request.min_years_experience,
        )
        overall_score = round(
            (title_score * 0.5)
            + (required_score * 0.35)
            + (nice_score * 0.1)
            + (experience_score * 0.05),
            4,
        )

        return JobSearchResult(
            resume_id=resume.resume_id,
            file_name=resume.file_name,
            source_path=resume.source_path,
            candidate_name=profile.candidate_name if profile else None,
            email=profile.email if profile else None,
            phone=profile.phone if profile else None,
            current_title=current_title,
            skills=parsed_skills,
            total_experience_years=profile.total_experience_years if profile else None,
            title_score=title_score,
            required_skill_score=required_score,
            nice_to_have_skill_score=nice_score,
            experience_score=experience_score,
            overall_score=overall_score,
            matched_required_skills=matched_required,
            missing_required_skills=missing_required,
            matched_nice_to_have_skills=matched_nice,
            match_reason=self._build_match_reason(
                title_score=title_score,
                candidate_years=profile.total_experience_years if profile else None,
                min_years_experience=request.min_years_experience,
                matched_required=matched_required,
                missing_required=missing_required,
                matched_nice=matched_nice,
            ),
        )

    def _is_searchable_resume(self, resume: ResumeRecord) -> bool:
        return (
            resume.extraction_status == "extracted"
            and resume.parsing_status in {"parsed", "review_required"}
            and resume.candidate_profile is not None
        )

    def _skill_score(self, matched_skills: list[str], requested_skills: list[str]) -> float:
        if not requested_skills:
            return 0
        return round(len(matched_skills) / len(requested_skills), 4)

    def _experience_score(
        self,
        candidate_years: float | None,
        min_years_experience: float,
    ) -> float:
        if min_years_experience <= 0:
            return 0
        if candidate_years is None:
            return 0
        return 1 if candidate_years >= min_years_experience else 0

    def _passes_experience_filter(
        self,
        candidate_years: float | None,
        min_years_experience: float,
    ) -> bool:
        if min_years_experience <= 0:
            return True
        if candidate_years is None:
            return False
        return candidate_years >= min_years_experience

    def _build_match_reason(
        self,
        title_score: float,
        candidate_years: float | None,
        min_years_experience: float,
        matched_required: list[str],
        missing_required: list[str],
        matched_nice: list[str],
    ) -> str:
        reason_parts = [f"Title matched with score {title_score}."]
        if min_years_experience > 0 and candidate_years is not None:
            reason_parts.append(
                "Experience requirement met: "
                f"{candidate_years:g} years >= {min_years_experience:g} years."
            )
        elif min_years_experience <= 0:
            reason_parts.append("No minimum experience requirement provided.")

        reason_parts.append(
            "Matched required skills: "
            f"{', '.join(matched_required) if matched_required else 'none'}."
        )
        reason_parts.append(
            "Missing required skills: "
            f"{', '.join(missing_required) if missing_required else 'none'}."
        )
        reason_parts.append(
            "Matched nice-to-have skills: "
            f"{', '.join(matched_nice) if matched_nice else 'none'}."
        )
        return " ".join(reason_parts)

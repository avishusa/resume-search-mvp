from app.repositories.resume_repository import InMemoryResumeRepository, ResumeRecord
from app.schemas.job import (
    JobSearchDebugExcludedCandidate,
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
            for resume in self._list_searchable_resumes()
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
        results = [
            self._score_resume(request, resume)
            for resume in title_matched_resumes
        ]
        ranked_results = sorted(
            results,
            key=lambda result: (
                result.required_skill_score,
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
            excluded_by_experience_count=sum(
                1
                for resume in title_matched_resumes
                if request.min_years_experience > 0
                and self._experience_passed(
                    resume.candidate_profile.total_experience_years
                    if resume.candidate_profile
                    else None,
                    request.min_years_experience,
                )
                is not True
            ),
            matched_count=len(ranked_results),
            results=ranked_results,
            debug_excluded_by_title=self._debug_excluded_by_title(
                request,
                candidates,
            )
            if request.debug
            else [],
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
        title_match = self._title_matcher.match(request.job_title, current_title)
        title_score = title_match.score
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
        missing_nice = [
            skill
            for skill in request.nice_to_have_skills
            if skill not in matched_nice
        ]
        required_score = self._skill_score(matched_required, request.required_skills)
        nice_score = self._skill_score(matched_nice, request.nice_to_have_skills)
        required_percentage = self._skill_match_percentage(
            matched_required,
            request.required_skills,
        )
        nice_percentage = self._skill_match_percentage(
            matched_nice,
            request.nice_to_have_skills,
        )
        experience_score = self._experience_score(
            profile.total_experience_years if profile else None,
            request.min_years_experience,
        )
        experience_passed = self._experience_passed(
            profile.total_experience_years if profile else None,
            request.min_years_experience,
        )
        recommendation_level = self._recommendation_level(
            title_score=title_score,
            required_skill_score=required_score,
            experience_passed=experience_passed,
            min_years_experience=request.min_years_experience,
        )
        shortlist_decision = self._shortlist_decision(recommendation_level)
        experience_reason = self._experience_match_reason(
            candidate_years=profile.total_experience_years if profile else None,
            min_years_experience=request.min_years_experience,
        )
        required_skill_reason = self._skill_match_reason(
            label="required",
            matched_skills=matched_required,
            missing_skills=missing_required,
            requested_skills=request.required_skills,
        )
        nice_skill_reason = self._skill_match_reason(
            label="nice-to-have",
            matched_skills=matched_nice,
            missing_skills=missing_nice,
            requested_skills=request.nice_to_have_skills,
            optional=True,
        )
        match_summary = self._build_match_summary(
            recommendation_level=recommendation_level,
            title_match_reason=title_match.reason,
            experience_reason=experience_reason,
            required_skill_reason=required_skill_reason,
            nice_skill_reason=nice_skill_reason,
        )
        overall_score = round(
            (title_score * 0.45)
            + (required_score * 0.4)
            + (experience_score * 0.1)
            + (nice_score * 0.05),
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
            shortlist_decision=shortlist_decision,
            recommendation_level=recommendation_level,
            match_summary=match_summary,
            matched_required_skills=matched_required,
            missing_required_skills=missing_required,
            matched_nice_to_have_skills=matched_nice,
            missing_nice_to_have_skills=missing_nice,
            required_skill_match_percentage=required_percentage,
            nice_to_have_skill_match_percentage=nice_percentage,
            match_reason=self._build_match_reason(
                match_summary=match_summary,
                nice_skill_reason=nice_skill_reason,
            ),
            title_match_type=title_match.match_type,
            title_match_reason=title_match.reason,
            jd_title_family=title_match.jd_title_family,
            candidate_title_family=title_match.candidate_title_family,
            experience_match_reason=experience_reason,
            required_skill_match_reason=required_skill_reason,
            nice_to_have_skill_match_reason=nice_skill_reason,
            title_passed=title_score > 0,
            experience_passed=experience_passed,
            skills_passed=not request.required_skills or required_score >= 0.8,
            final_exclusion_reason=None,
            normalized_jd_title=title_match.normalized_jd_title
            if request.debug
            else None,
            normalized_candidate_title=title_match.normalized_candidate_title
            if request.debug
            else None,
        )

    def _is_searchable_resume(self, resume: ResumeRecord) -> bool:
        return (
            resume.extraction_status == "extracted"
            and resume.parsing_status in {"parsed", "review_required"}
            and resume.candidate_profile is not None
        )

    def _list_searchable_resumes(self) -> list[ResumeRecord]:
        if hasattr(self._repository, "list_searchable"):
            return self._repository.list_searchable()
        return self._repository.list_all()

    def _skill_score(self, matched_skills: list[str], requested_skills: list[str]) -> float:
        if not requested_skills:
            return 0
        return round(len(matched_skills) / len(requested_skills), 4)

    def _skill_match_percentage(
        self,
        matched_skills: list[str],
        requested_skills: list[str],
    ) -> float:
        if not requested_skills:
            return 0
        return round((len(matched_skills) / len(requested_skills)) * 100, 1)

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

    def _experience_passed(
        self,
        candidate_years: float | None,
        min_years_experience: float,
    ) -> bool | None:
        if min_years_experience <= 0:
            return None
        if candidate_years is None:
            return None
        return candidate_years >= min_years_experience

    def _recommendation_level(
        self,
        title_score: float,
        required_skill_score: float,
        experience_passed: bool | None,
        min_years_experience: float,
    ) -> str:
        if min_years_experience > 0 and experience_passed is False:
            return "weak_match"

        experience_requirement_met = min_years_experience <= 0 or experience_passed is True
        if (
            title_score > 0
            and required_skill_score >= 0.8
            and experience_requirement_met
        ):
            return "strong_match"
        if title_score > 0 and required_skill_score >= 0.5:
            return "moderate_match"
        return "weak_match"

    def _shortlist_decision(self, recommendation_level: str) -> str:
        if recommendation_level == "strong_match":
            return "shortlist"
        if recommendation_level == "moderate_match":
            return "review"
        return "not_recommended"

    def _experience_match_reason(
        self,
        candidate_years: float | None,
        min_years_experience: float,
    ) -> str:
        if min_years_experience <= 0:
            return "No minimum experience requirement provided."
        if candidate_years is None:
            return "Experience unknown; requirement could not be verified."
        if candidate_years < min_years_experience:
            return (
                "Experience requirement not met: "
                f"{candidate_years:g} years < {min_years_experience:g} years."
            )
        return (
            "Experience requirement met: "
            f"{candidate_years:g} years >= {min_years_experience:g} years."
        )

    def _skill_match_reason(
        self,
        label: str,
        matched_skills: list[str],
        missing_skills: list[str],
        requested_skills: list[str],
        optional: bool = False,
    ) -> str:
        if not requested_skills:
            return f"No {label} skills requested."

        skill_label = f"optional {label}" if optional else label
        reason = f"Matched {len(matched_skills)}/{len(requested_skills)} {skill_label} skills"
        if matched_skills:
            reason += f": {', '.join(matched_skills)}"
        else:
            reason += ": none"

        if missing_skills:
            missing_label = (
                "Missing optional nice-to-have skills"
                if optional
                else f"Missing {label} skills"
            )
            reason += f". {missing_label}: {', '.join(missing_skills)}."
        else:
            no_missing_label = (
                "No optional nice-to-have gaps"
                if optional
                else f"No missing {label} skills"
            )
            reason += f". {no_missing_label}."
        return reason

    def _build_match_summary(
        self,
        recommendation_level: str,
        title_match_reason: str,
        experience_reason: str,
        required_skill_reason: str,
        nice_skill_reason: str,
    ) -> str:
        label = {
            "strong_match": "Strong match",
            "moderate_match": "Review",
            "weak_match": "Not recommended",
        }[recommendation_level]
        return (
            f"{label}: {title_match_reason} "
            f"{experience_reason} {required_skill_reason} {nice_skill_reason}"
        )

    def _build_match_reason(
        self,
        match_summary: str,
        nice_skill_reason: str,
    ) -> str:
        return match_summary

    def _debug_excluded_by_title(
        self,
        request: JobSearchRequest,
        candidates: list[ResumeRecord],
    ) -> list[JobSearchDebugExcludedCandidate]:
        excluded_candidates: list[JobSearchDebugExcludedCandidate] = []
        for resume in candidates:
            profile = resume.candidate_profile
            current_title = profile.current_title if profile else None
            title_match = self._title_matcher.match(request.job_title, current_title)
            if title_match.score > 0:
                continue

            excluded_candidates.append(
                JobSearchDebugExcludedCandidate(
                    resume_id=resume.resume_id,
                    file_name=resume.file_name,
                    source_path=resume.source_path,
                    current_title=current_title,
                    title_score=title_match.score,
                    title_match_type=title_match.match_type,
                    title_match_reason=title_match.reason,
                    jd_title_family=title_match.jd_title_family,
                    candidate_title_family=title_match.candidate_title_family,
                    normalized_jd_title=title_match.normalized_jd_title,
                    normalized_candidate_title=title_match.normalized_candidate_title,
                    final_exclusion_reason="Excluded because strict title matching failed.",
                )
            )
        return excluded_candidates

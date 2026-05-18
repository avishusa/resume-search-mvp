from pydantic import BaseModel, Field


class JobSearchRequest(BaseModel):
    job_title: str
    job_description: str
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    min_years_experience: float = 0
    debug: bool = False


class JobSearchQuery(BaseModel):
    job_title: str
    required_skills: list[str]
    nice_to_have_skills: list[str]


class JobSearchResult(BaseModel):
    resume_id: str
    file_name: str
    source_path: str | None
    candidate_name: str | None
    email: str | None
    phone: str | None
    current_title: str | None
    skills: list[str]
    total_experience_years: float | None
    title_score: float
    required_skill_score: float
    nice_to_have_skill_score: float
    experience_score: float
    overall_score: float
    shortlist_decision: str
    recommendation_level: str
    match_summary: str
    matched_required_skills: list[str]
    missing_required_skills: list[str]
    matched_nice_to_have_skills: list[str]
    missing_nice_to_have_skills: list[str]
    required_skill_match_percentage: float
    nice_to_have_skill_match_percentage: float
    match_reason: str
    title_match_type: str
    title_match_reason: str
    jd_title_family: str | None = None
    candidate_title_family: str | None = None
    experience_match_reason: str
    required_skill_match_reason: str
    nice_to_have_skill_match_reason: str
    title_passed: bool
    experience_passed: bool | None
    skills_passed: bool
    final_exclusion_reason: str | None = None
    normalized_jd_title: str | None = None
    normalized_candidate_title: str | None = None


class JobSearchDebugExcludedCandidate(BaseModel):
    resume_id: str
    file_name: str
    source_path: str | None
    current_title: str | None
    title_score: float
    title_match_type: str
    title_match_reason: str
    jd_title_family: str | None = None
    candidate_title_family: str | None = None
    normalized_jd_title: str
    normalized_candidate_title: str
    final_exclusion_reason: str


class JobSearchResponse(BaseModel):
    query: JobSearchQuery
    total_candidates_considered: int
    excluded_by_title_count: int
    excluded_by_experience_count: int
    matched_count: int
    results: list[JobSearchResult]
    debug_excluded_by_title: list[JobSearchDebugExcludedCandidate] = Field(
        default_factory=list
    )

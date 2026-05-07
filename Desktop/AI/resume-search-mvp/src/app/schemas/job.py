from pydantic import BaseModel, Field


class JobSearchRequest(BaseModel):
    job_title: str
    job_description: str
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    min_years_experience: float = 0


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
    matched_required_skills: list[str]
    missing_required_skills: list[str]
    matched_nice_to_have_skills: list[str]
    match_reason: str


class JobSearchResponse(BaseModel):
    query: JobSearchQuery
    total_candidates_considered: int
    excluded_by_title_count: int
    excluded_by_experience_count: int
    matched_count: int
    results: list[JobSearchResult]

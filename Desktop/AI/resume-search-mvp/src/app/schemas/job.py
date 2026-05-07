from pydantic import BaseModel, Field


class JobSearchRequest(BaseModel):
    job_title: str
    job_description: str
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)


class JobSearchResult(BaseModel):
    resume_id: str
    file_name: str
    source_path: str | None
    current_title: str | None
    title_score: int
    required_skill_score: int
    nice_to_have_skill_score: int
    overall_score: int
    matched_required_skills: list[str]
    missing_required_skills: list[str]
    matched_nice_to_have_skills: list[str]
    explanation: str


class JobSearchResponse(BaseModel):
    results: list[JobSearchResult]

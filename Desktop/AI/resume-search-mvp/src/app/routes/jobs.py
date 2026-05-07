from fastapi import APIRouter

from app.container import resume_search_service
from app.schemas.job import JobSearchRequest, JobSearchResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/search", response_model=JobSearchResponse)
def search_jobs(request: JobSearchRequest) -> JobSearchResponse:
    return resume_search_service.search(request)

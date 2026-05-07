from fastapi import FastAPI

from app.config import get_settings
from app.routes.debug import router as debug_router
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.routes.resumes import router as resumes_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.include_router(health_router)
    app.include_router(resumes_router)
    app.include_router(jobs_router)
    app.include_router(debug_router)
    return app


app = create_app()

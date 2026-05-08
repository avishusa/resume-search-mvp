from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.container import batch_processing_service
from app.config import get_settings
from app.database import init_db
from app.routes.batch import router as batch_router
from app.routes.debug import router as debug_router
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.routes.resumes import router as resumes_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def initialize_database() -> None:
        init_db()
        batch_processing_service.start_scheduler_if_enabled(
            enabled=settings.enable_nightly_batch,
            hour=settings.nightly_batch_hour,
            minute=settings.nightly_batch_minute,
        )

    app.include_router(health_router)
    app.include_router(batch_router)
    app.include_router(resumes_router)
    app.include_router(jobs_router)
    app.include_router(debug_router)
    return app


app = create_app()

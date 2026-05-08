from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.database import SessionLocal, init_db
from app.models.batch_run import BatchRunModel
from app.schemas.resume import LocalDriveIngestionResponse


@dataclass(frozen=True)
class BatchRunRecord:
    batch_id: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    total_files_seen: int = 0
    ingested_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    parsed_count: int = 0
    fallback_count: int = 0
    error_message: str | None = None


class BatchRunRepository:
    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        init_db()
        self._session_factory = session_factory

    def create_running(self) -> BatchRunRecord:
        batch_id = str(uuid4())
        started_at = datetime.now(UTC)
        with self._session_factory() as session:
            model = BatchRunModel(
                batch_id=batch_id,
                started_at=started_at,
                status="running",
            )
            session.add(model)
            session.commit()
        return BatchRunRecord(
            batch_id=batch_id,
            started_at=started_at,
            finished_at=None,
            status="running",
        )

    def mark_completed(
        self,
        batch_id: str,
        summary: LocalDriveIngestionResponse,
    ) -> BatchRunRecord:
        return self._finish(
            batch_id=batch_id,
            status="completed",
            summary=summary,
            error_message=None,
        )

    def mark_failed(self, batch_id: str, error_message: str) -> BatchRunRecord:
        return self._finish(
            batch_id=batch_id,
            status="failed",
            summary=None,
            error_message=error_message,
        )

    def get(self, batch_id: str) -> BatchRunRecord | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(BatchRunModel).where(BatchRunModel.batch_id == batch_id)
            )
            return self._to_record(model) if model else None

    def get_active_running(self) -> BatchRunRecord | None:
        with self._session_factory() as session:
            model = session.scalar(
                select(BatchRunModel)
                .where(BatchRunModel.status == "running")
                .order_by(BatchRunModel.started_at.desc())
                .limit(1)
            )
            return self._to_record(model) if model else None

    def list_recent(self, limit: int = 20) -> list[BatchRunRecord]:
        with self._session_factory() as session:
            models = session.scalars(
                select(BatchRunModel)
                .order_by(BatchRunModel.started_at.desc())
                .limit(limit)
            ).all()
            return [self._to_record(model) for model in models]

    def mark_running_as_interrupted(self) -> int:
        finished_at = datetime.now(UTC)
        with self._session_factory() as session:
            models = session.scalars(
                select(BatchRunModel).where(BatchRunModel.status == "running")
            ).all()
            for model in models:
                model.status = "failed"
                model.finished_at = finished_at
                model.error_message = (
                    "Batch was marked failed because the application restarted "
                    "before it completed."
                )
            session.commit()
            return len(models)

    def clear(self) -> None:
        with self._session_factory() as session:
            session.query(BatchRunModel).delete()
            session.commit()

    def _finish(
        self,
        batch_id: str,
        status: str,
        summary: LocalDriveIngestionResponse | None,
        error_message: str | None,
    ) -> BatchRunRecord:
        finished_at = datetime.now(UTC)
        with self._session_factory() as session:
            model = session.scalar(
                select(BatchRunModel).where(BatchRunModel.batch_id == batch_id)
            )
            if model is None:
                raise ValueError(f"Batch run not found: {batch_id}")

            model.finished_at = finished_at
            model.status = status
            model.error_message = error_message
            if summary is not None:
                model.total_files_seen = summary.total_files_seen
                model.ingested_count = summary.ingested_count
                model.updated_count = summary.updated_count
                model.skipped_count = summary.skipped_count
                model.failed_count = summary.failed_count
                model.parsed_count = summary.parsed_count
                model.fallback_count = summary.fallback_count
            session.commit()
            session.refresh(model)
            return self._to_record(model)

    def _to_record(self, model: BatchRunModel) -> BatchRunRecord:
        return BatchRunRecord(
            batch_id=model.batch_id,
            started_at=model.started_at,
            finished_at=model.finished_at,
            status=model.status,
            total_files_seen=model.total_files_seen,
            ingested_count=model.ingested_count,
            updated_count=model.updated_count,
            skipped_count=model.skipped_count,
            failed_count=model.failed_count,
            parsed_count=model.parsed_count,
            fallback_count=model.fallback_count,
            error_message=model.error_message,
        )

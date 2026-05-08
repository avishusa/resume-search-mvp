from threading import Lock

from app.repositories.batch_run_repository import BatchRunRecord, BatchRunRepository
from app.schemas.resume import LocalDriveIngestionResponse
from app.services.resume_batch_processor import ResumeBatchProcessor


class BatchAlreadyRunningError(RuntimeError):
    pass


class ResumeBatchProcessingService:
    def __init__(
        self,
        batch_processor: ResumeBatchProcessor,
        batch_run_repository: BatchRunRepository,
    ) -> None:
        self._batch_processor = batch_processor
        self._batch_run_repository = batch_run_repository
        self._lock = Lock()

    def run_local_drive_batch(
        self,
        force: bool = False,
    ) -> tuple[BatchRunRecord, LocalDriveIngestionResponse]:
        if not self._lock.acquire(blocking=False):
            raise BatchAlreadyRunningError("A resume batch is already running.")

        batch_run = self._batch_run_repository.create_running()
        try:
            summary = self._batch_processor.process_local_drive(force=force)
            completed_run = self._batch_run_repository.mark_completed(
                batch_id=batch_run.batch_id,
                summary=summary,
            )
            return completed_run, summary
        except Exception as exception:
            self._batch_run_repository.mark_failed(
                batch_id=batch_run.batch_id,
                error_message=str(exception),
            )
            raise
        finally:
            self._lock.release()

    def list_recent_runs(self) -> list[BatchRunRecord]:
        return self._batch_run_repository.list_recent()

    def get_run(self, batch_id: str) -> BatchRunRecord | None:
        return self._batch_run_repository.get(batch_id)

    def start_scheduler_if_enabled(
        self,
        enabled: bool,
        hour: int,
        minute: int,
    ) -> None:
        # Placeholder for APScheduler/cron integration in a later step.
        # Kept intentionally no-op unless a real scheduler is introduced.
        return None


def run_nightly_resume_batch(
    batch_processing_service: ResumeBatchProcessingService,
) -> tuple[BatchRunRecord, LocalDriveIngestionResponse]:
    return batch_processing_service.run_local_drive_batch(force=False)

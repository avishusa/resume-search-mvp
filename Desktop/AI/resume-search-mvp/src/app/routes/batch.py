from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.container import batch_processing_service
from app.schemas.batch import (
    ActiveBatchRunResponse,
    BatchRunListResponse,
    BatchRunResponse,
)
from app.services.batch_processing_service import BatchAlreadyRunningError

router = APIRouter(prefix="/batch", tags=["batch"])


@router.post("/run-local-drive", response_model=BatchRunResponse)
def run_local_drive_batch(force: bool = False) -> BatchRunResponse:
    try:
        batch_run, _summary = batch_processing_service.run_local_drive_batch(force=force)
    except BatchAlreadyRunningError as error:
        raise _batch_already_running_http_error(error) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    return _to_response(batch_run)


@router.post("/run", response_model=BatchRunResponse)
def run_configured_batch(force: bool = False) -> BatchRunResponse:
    try:
        batch_run, _summary = batch_processing_service.run_batch(force=force)
    except BatchAlreadyRunningError as error:
        raise _batch_already_running_http_error(error) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error
    return _to_response(batch_run)


@router.get("/runs", response_model=BatchRunListResponse)
def list_batch_runs() -> BatchRunListResponse:
    return BatchRunListResponse(
        runs=[_to_response(batch_run) for batch_run in batch_processing_service.list_recent_runs()]
    )


@router.get("/runs/active", response_model=ActiveBatchRunResponse)
def get_active_batch_run() -> ActiveBatchRunResponse:
    active_run = batch_processing_service.get_active_run()
    if active_run is None:
        return ActiveBatchRunResponse(is_running=False)
    return ActiveBatchRunResponse(
        is_running=True,
        batch_id=active_run.batch_id,
        started_at=_datetime_to_iso(active_run.started_at),
        status=active_run.status,
    )


@router.get("/runs/{batch_id}", response_model=BatchRunResponse)
def get_batch_run(batch_id: str) -> BatchRunResponse:
    batch_run = batch_processing_service.get_run(batch_id)
    if batch_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch run not found.",
        )
    return _to_response(batch_run)


def _to_response(batch_run) -> BatchRunResponse:
    return BatchRunResponse(
        batch_id=batch_run.batch_id,
        started_at=_datetime_to_iso(batch_run.started_at),
        finished_at=_datetime_to_iso(batch_run.finished_at)
        if batch_run.finished_at
        else None,
        status=batch_run.status,
        total_files_seen=batch_run.total_files_seen,
        ingested_count=batch_run.ingested_count,
        updated_count=batch_run.updated_count,
        skipped_count=batch_run.skipped_count,
        failed_count=batch_run.failed_count,
        parsed_count=batch_run.parsed_count,
        fallback_count=batch_run.fallback_count,
        error_message=batch_run.error_message,
    )


def _batch_already_running_http_error(error: BatchAlreadyRunningError) -> HTTPException:
    active_batch = error.active_batch
    detail = {
        "message": "A batch run is already in progress.",
        "batch_id": active_batch.batch_id if active_batch else None,
        "started_at": _datetime_to_iso(active_batch.started_at)
        if active_batch
        else None,
    }
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


def _datetime_to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()

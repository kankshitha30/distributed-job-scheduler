from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.job import (
    JobCreate,
    JobBatchCreate,
    JobResponse,
    JobDetailResponse,
    DeadLetterResponse,
)
from app.schemas.execution import JobExecutionResponse, JobLogResponse
from app.services.job_service import job_service
from app.utils.security import get_current_user
from app.utils.pagination import PaginatedResponse

router = APIRouter(tags=["Jobs"])


def build_job_response(j, queue_name: Optional[str] = None) -> JobResponse:
    q_name = queue_name
    if q_name is None and "queue" in j.__dict__ and j.queue:
        q_name = j.queue.name

    return JobResponse(
        id=j.id,
        queue_id=j.queue_id,
        queue_name=q_name,
        job_type=j.job_type,
        payload=j.payload,
        status=j.status,
        priority=j.priority,
        scheduled_at=j.scheduled_at,
        available_at=j.available_at,
        attempts=j.attempts,
        max_attempts=j.max_attempts,
        created_at=j.created_at,
        updated_at=j.updated_at,
        completed_at=j.completed_at,
    )


@router.post("/queues/{queue_id}/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    queue_id: str,
    req: JobCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await job_service.create_job(db, queue_id, req, idempotency_key)
    return build_job_response(job)


@router.post("/queues/{queue_id}/jobs/batch", response_model=List[JobResponse], status_code=status.HTTP_201_CREATED)
async def create_batch_jobs(
    queue_id: str,
    req: JobBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    jobs = await job_service.create_batch_jobs(db, queue_id, req)
    return [build_job_response(j) for j in jobs]


@router.get("/jobs", response_model=PaginatedResponse[JobResponse])
async def list_jobs(
    queue_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    priority: Optional[int] = Query(None),
    worker_id: Optional[str] = Query(None),
    created_after: Optional[datetime] = Query(None),
    created_before: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    jobs, total = await job_service.list_jobs(
        db=db,
        queue_id=queue_id,
        status_filter=status,
        job_type=job_type,
        priority=priority,
        worker_id=worker_id,
        created_after=created_after,
        created_before=created_before,
        page=page,
        page_size=page_size,
    )
    items = [build_job_response(j) for j in jobs]
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = await job_service.get_job(db, job_id)

    executions = [
        JobExecutionResponse(
            id=ex.id,
            job_id=ex.job_id,
            worker_id=ex.worker_id,
            attempt_number=ex.attempt_number,
            status=ex.status,
            started_at=ex.started_at,
            completed_at=ex.completed_at,
            duration_ms=ex.duration_ms,
            error_message=ex.error_message,
        )
        for ex in job.executions
    ]

    logs = [
        JobLogResponse(
            id=lg.id,
            job_id=lg.job_id,
            execution_id=lg.execution_id,
            level=lg.level,
            message=lg.message,
            timestamp=lg.timestamp,
        )
        for lg in job.logs
    ]

    dl_resp = None
    if "dead_letter_entry" in job.__dict__ and job.dead_letter_entry:
        dl_resp = DeadLetterResponse(
            id=job.dead_letter_entry.id,
            job_id=job.dead_letter_entry.job_id,
            reason=job.dead_letter_entry.reason,
            final_error=job.dead_letter_entry.final_error,
            failed_at=job.dead_letter_entry.failed_at,
            retry_count=job.dead_letter_entry.retry_count,
        )

    q_name = job.queue.name if ("queue" in job.__dict__ and job.queue) else None

    return JobDetailResponse(
        id=job.id,
        queue_id=job.queue_id,
        queue_name=q_name,
        job_type=job.job_type,
        payload=job.payload,
        status=job.status,
        priority=job.priority,
        scheduled_at=job.scheduled_at,
        available_at=job.available_at,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        executions=executions,
        logs=logs,
        dead_letter=dl_resp,
    )


@router.post("/jobs/{job_id}/retry", response_model=JobDetailResponse)
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await job_service.retry_dead_letter_job(db, job_id)
    return await get_job(job_id=job_id, db=db, current_user=current_user)


@router.get("/jobs/{job_id}/executions", response_model=List[JobExecutionResponse])
async def get_job_executions(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    executions = await job_service.get_job_executions(db, job_id)
    return [
        JobExecutionResponse(
            id=ex.id,
            job_id=ex.job_id,
            worker_id=ex.worker_id,
            attempt_number=ex.attempt_number,
            status=ex.status,
            started_at=ex.started_at,
            completed_at=ex.completed_at,
            duration_ms=ex.duration_ms,
            error_message=ex.error_message,
        )
        for ex in executions
    ]


@router.get("/jobs/{job_id}/logs", response_model=List[JobLogResponse])
async def get_job_logs(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = await job_service.get_job_logs(db, job_id)
    return [
        JobLogResponse(
            id=lg.id,
            job_id=lg.job_id,
            execution_id=lg.execution_id,
            level=lg.level,
            message=lg.message,
            timestamp=lg.timestamp,
        )
        for lg in logs
    ]

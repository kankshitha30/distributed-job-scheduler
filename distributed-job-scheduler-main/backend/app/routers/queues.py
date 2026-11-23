from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.queue import QueueCreate, QueueUpdate, QueueResponse, QueueStats
from app.schemas.job import JobResponse
from app.schemas.retry_policy import RetryPolicyResponse
from app.services.queue_service import queue_service
from app.services.job_service import job_service
from app.utils.security import get_current_user
from app.utils.pagination import PaginatedResponse

router = APIRouter(tags=["Queues"])


def build_queue_response(queue, stats: Optional[QueueStats] = None) -> QueueResponse:
    rp_resp = None
    if queue.retry_policy:
        rp_resp = RetryPolicyResponse(
            id=queue.retry_policy.id,
            name=queue.retry_policy.name,
            strategy=queue.retry_policy.strategy,
            max_attempts=queue.retry_policy.max_attempts,
            initial_delay_seconds=queue.retry_policy.initial_delay_seconds,
            backoff_multiplier=queue.retry_policy.backoff_multiplier,
        )
    return QueueResponse(
        id=queue.id,
        project_id=queue.project_id,
        name=queue.name,
        priority=queue.priority,
        concurrency_limit=queue.concurrency_limit,
        paused=queue.paused,
        retry_policy_id=queue.retry_policy_id,
        created_at=queue.created_at,
        updated_at=queue.updated_at,
        retry_policy=rp_resp,
        stats=stats,
    )


@router.post("/projects/{project_id}/queues", response_model=QueueResponse, status_code=status.HTTP_201_CREATED)
async def create_queue(
    project_id: str,
    req: QueueCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    queue = await queue_service.create_queue(db, project_id, req)
    stats = await queue_service.get_queue_stats(db, queue.id)
    return build_queue_response(queue, stats)


@router.get("/projects/{project_id}/queues", response_model=List[QueueResponse])
async def list_project_queues(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    queues = await queue_service.list_queues_by_project(db, project_id)
    results = []
    for q in queues:
        stats = await queue_service.get_queue_stats(db, q.id)
        results.append(build_queue_response(q, stats))
    return results


@router.get("/queues", response_model=List[QueueResponse])
async def list_all_queues(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    queues = await queue_service.list_all_queues(db)
    results = []
    for q in queues:
        stats = await queue_service.get_queue_stats(db, q.id)
        results.append(build_queue_response(q, stats))
    return results


@router.get("/queues/{queue_id}", response_model=QueueResponse)
async def get_queue(
    queue_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    queue = await queue_service.get_queue(db, queue_id)
    stats = await queue_service.get_queue_stats(db, queue_id)
    return build_queue_response(queue, stats)


@router.put("/queues/{queue_id}", response_model=QueueResponse)
async def update_queue(
    queue_id: str,
    req: QueueUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    queue = await queue_service.update_queue(db, queue_id, req)
    stats = await queue_service.get_queue_stats(db, queue_id)
    return build_queue_response(queue, stats)


@router.delete("/queues/{queue_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_queue(
    queue_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await queue_service.delete_queue(db, queue_id)
    return None


@router.post("/queues/{queue_id}/pause", response_model=QueueResponse)
async def pause_queue(
    queue_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    queue = await queue_service.set_paused(db, queue_id, True)
    stats = await queue_service.get_queue_stats(db, queue_id)
    return build_queue_response(queue, stats)


@router.post("/queues/{queue_id}/resume", response_model=QueueResponse)
async def resume_queue(
    queue_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    queue = await queue_service.set_paused(db, queue_id, False)
    stats = await queue_service.get_queue_stats(db, queue_id)
    return build_queue_response(queue, stats)


@router.get("/queues/{queue_id}/stats", response_model=QueueStats)
async def get_queue_statistics(
    queue_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await queue_service.get_queue_stats(db, queue_id)


@router.get("/queues/{queue_id}/dead-letter", response_model=PaginatedResponse[JobResponse])
async def get_queue_dead_letters(
    queue_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    jobs, total = await job_service.get_dead_letter_jobs(db, queue_id=queue_id, page=page, page_size=page_size)
    items = [
        JobResponse(
            id=j.id,
            queue_id=j.queue_id,
            queue_name=j.queue.name if j.queue else None,
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
        for j in jobs
    ]
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)

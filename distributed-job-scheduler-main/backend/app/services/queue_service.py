import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload
from fastapi import status

from app.models.project import Queue, Project, RetryPolicy
from app.models.job import Job, JobExecution
from app.schemas.queue import QueueCreate, QueueUpdate, QueueStats
from app.middleware.error_handler import AppException


class QueueService:
    @staticmethod
    async def create_queue(
        db: AsyncSession,
        project_id: str,
        data: QueueCreate,
    ) -> Queue:
        # Check project exists
        proj_res = await db.execute(select(Project).where(Project.id == project_id))
        if not proj_res.scalar_one_or_none():
            raise AppException(
                code="PROJECT_NOT_FOUND",
                message=f"Project with ID {project_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Check unique queue name in project
        existing_res = await db.execute(
            select(Queue).where(Queue.project_id == project_id, Queue.name == data.name.strip())
        )
        if existing_res.scalar_one_or_none():
            raise AppException(
                code="QUEUE_ALREADY_EXISTS",
                message=f"A queue named '{data.name}' already exists in this project",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Check retry policy if specified
        if data.retry_policy_id:
            rp_res = await db.execute(select(RetryPolicy).where(RetryPolicy.id == data.retry_policy_id))
            if not rp_res.scalar_one_or_none():
                raise AppException(
                    code="RETRY_POLICY_NOT_FOUND",
                    message=f"Retry policy {data.retry_policy_id} does not exist",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

        queue = Queue(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=data.name.strip(),
            priority=data.priority,
            concurrency_limit=data.concurrency_limit,
            retry_policy_id=data.retry_policy_id,
            paused=False,
        )
        db.add(queue)
        await db.commit()

        # Reload with relations
        stmt = (
            select(Queue)
            .where(Queue.id == queue.id)
            .options(selectinload(Queue.retry_policy))
        )
        res = await db.execute(stmt)
        return res.scalar_one()

    @staticmethod
    async def get_queue(db: AsyncSession, queue_id: str) -> Queue:
        stmt = (
            select(Queue)
            .where(Queue.id == queue_id)
            .options(selectinload(Queue.retry_policy))
        )
        res = await db.execute(stmt)
        queue = res.scalar_one_or_none()
        if not queue:
            raise AppException(
                code="QUEUE_NOT_FOUND",
                message=f"Queue with ID {queue_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return queue

    @staticmethod
    async def list_queues_by_project(db: AsyncSession, project_id: str) -> List[Queue]:
        stmt = (
            select(Queue)
            .where(Queue.project_id == project_id)
            .options(selectinload(Queue.retry_policy))
            .order_by(Queue.priority.desc(), Queue.name.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def list_all_queues(db: AsyncSession) -> List[Queue]:
        stmt = (
            select(Queue)
            .options(selectinload(Queue.retry_policy))
            .order_by(Queue.priority.desc(), Queue.name.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def update_queue(db: AsyncSession, queue_id: str, data: QueueUpdate) -> Queue:
        queue = await QueueService.get_queue(db, queue_id)

        if data.name is not None and data.name.strip() != queue.name:
            # Check duplicate name
            existing_res = await db.execute(
                select(Queue).where(
                    Queue.project_id == queue.project_id,
                    Queue.name == data.name.strip(),
                    Queue.id != queue_id,
                )
            )
            if existing_res.scalar_one_or_none():
                raise AppException(
                    code="QUEUE_ALREADY_EXISTS",
                    message=f"A queue named '{data.name}' already exists in this project",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            queue.name = data.name.strip()

        if data.priority is not None:
            queue.priority = data.priority
        if data.concurrency_limit is not None:
            queue.concurrency_limit = data.concurrency_limit
        if data.retry_policy_id is not None:
            if data.retry_policy_id:
                rp_res = await db.execute(select(RetryPolicy).where(RetryPolicy.id == data.retry_policy_id))
                if not rp_res.scalar_one_or_none():
                    raise AppException(
                        code="RETRY_POLICY_NOT_FOUND",
                        message=f"Retry policy {data.retry_policy_id} not found",
                        status_code=status.HTTP_404_NOT_FOUND,
                    )
            queue.retry_policy_id = data.retry_policy_id or None
        if data.paused is not None:
            queue.paused = data.paused

        await db.commit()
        return await QueueService.get_queue(db, queue_id)

    @staticmethod
    async def delete_queue(db: AsyncSession, queue_id: str) -> None:
        queue = await QueueService.get_queue(db, queue_id)
        await db.delete(queue)
        await db.commit()

    @staticmethod
    async def set_paused(db: AsyncSession, queue_id: str, paused: bool) -> Queue:
        queue = await QueueService.get_queue(db, queue_id)
        queue.paused = paused
        await db.commit()
        return queue

    @staticmethod
    async def get_queue_stats(db: AsyncSession, queue_id: str) -> QueueStats:
        # Status counts
        status_stmt = (
            select(Job.status, func.count(Job.id))
            .where(Job.queue_id == queue_id)
            .group_by(Job.status)
        )
        res = await db.execute(status_stmt)
        counts = {status_name: count for status_name, count in res.all()}

        total_jobs = sum(counts.values())
        queued_jobs = counts.get("QUEUED", 0) + counts.get("SCHEDULED", 0)
        running_jobs = counts.get("RUNNING", 0) + counts.get("CLAIMED", 0)
        completed_jobs = counts.get("COMPLETED", 0)
        failed_jobs = counts.get("FAILED", 0)
        retrying_jobs = counts.get("RETRYING", 0)
        dead_letter_jobs = counts.get("DEAD_LETTER", 0)

        # Average duration of completed executions
        avg_stmt = (
            select(func.avg(JobExecution.duration_ms))
            .join(Job, JobExecution.job_id == Job.id)
            .where(Job.queue_id == queue_id, JobExecution.status == "COMPLETED", JobExecution.duration_ms.is_not(None))
        )
        avg_res = await db.execute(avg_stmt)
        avg_duration = avg_res.scalar_one_or_none() or 0.0

        # Success rate
        finished_jobs = completed_jobs + failed_jobs + dead_letter_jobs
        success_rate = (completed_jobs / finished_jobs * 100.0) if finished_jobs > 0 else 100.0

        return QueueStats(
            total_jobs=total_jobs,
            queued_jobs=queued_jobs,
            running_jobs=running_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            retrying_jobs=retrying_jobs,
            dead_letter_jobs=dead_letter_jobs,
            average_execution_time_ms=round(float(avg_duration), 2),
            success_rate=round(float(success_rate), 2),
        )


queue_service = QueueService()

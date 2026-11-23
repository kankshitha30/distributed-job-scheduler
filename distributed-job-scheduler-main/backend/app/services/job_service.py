import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any
from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc, delete
from sqlalchemy.orm import selectinload
from fastapi import status

from app.models.project import Queue, RetryPolicy
from app.models.job import Job, JobExecution, JobLog, ScheduledJob, DeadLetterJob
from app.schemas.job import JobCreate, JobBatchCreate
from app.middleware.error_handler import AppException


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobService:
    @staticmethod
    def calculate_retry_delay(
        strategy: str,
        attempt: int,
        initial_delay: int = 5,
        multiplier: float = 2.0,
    ) -> int:
        """
        Calculates retry delay in seconds according to policy:
        - fixed: initial_delay
        - linear: initial_delay * attempt
        - exponential: initial_delay * (multiplier ^ (attempt - 1))
        """
        attempt = max(1, attempt)
        if strategy == "fixed":
            return initial_delay
        elif strategy == "linear":
            return int(initial_delay * attempt)
        elif strategy == "exponential":
            return int(initial_delay * (multiplier ** (attempt - 1)))
        return initial_delay

    @staticmethod
    async def create_job(
        db: AsyncSession,
        queue_id: str,
        data: JobCreate,
        idempotency_key: Optional[str] = None,
    ) -> Job:
        # Check queue exists and load retry policy
        stmt_q = (
            select(Queue)
            .where(Queue.id == queue_id)
            .options(selectinload(Queue.retry_policy))
        )
        res_q = await db.execute(stmt_q)
        queue = res_q.scalar_one_or_none()
        if not queue:
            raise AppException(
                code="QUEUE_NOT_FOUND",
                message=f"Queue with ID {queue_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Idempotency check
        if idempotency_key:
            stmt_idem = select(Job).where(Job.idempotency_key == idempotency_key.strip())
            res_idem = await db.execute(stmt_idem)
            existing_job = res_idem.scalar_one_or_none()
            if existing_job:
                return existing_job

        now = utcnow()
        available_at = now
        initial_status = "QUEUED"

        # Calculate scheduled / delayed availability
        if data.delay_seconds is not None and data.delay_seconds > 0:
            available_at = now + timedelta(seconds=data.delay_seconds)
            initial_status = "SCHEDULED"
        elif data.scheduled_at is not None:
            # Ensure scheduled_at is tz-aware UTC
            sched = data.scheduled_at
            if sched.tzinfo is None:
                sched = sched.replace(tzinfo=timezone.utc)
            available_at = sched
            if available_at > now:
                initial_status = "SCHEDULED"

        # Determine max_attempts
        max_attempts = 3
        if data.max_attempts is not None:
            max_attempts = data.max_attempts
        elif queue.retry_policy:
            max_attempts = queue.retry_policy.max_attempts

        job_id = str(uuid.uuid4())
        job = Job(
            id=job_id,
            queue_id=queue_id,
            job_type=data.job_type.strip(),
            payload=data.payload or {},
            status=initial_status,
            priority=data.priority,
            scheduled_at=data.scheduled_at,
            available_at=available_at,
            attempts=0,
            max_attempts=max_attempts,
            idempotency_key=idempotency_key.strip() if idempotency_key else None,
            created_at=now,
            updated_at=now,
        )
        db.add(job)

        # Add initial audit log
        log_msg = f"Job created with status={initial_status}, available_at={available_at.isoformat()}"
        if idempotency_key:
            log_msg += f", idempotency_key={idempotency_key}"
        job_log = JobLog(
            id=str(uuid.uuid4()),
            job_id=job_id,
            level="INFO",
            message=log_msg,
            timestamp=now,
        )
        db.add(job_log)

        # Recurring job handling with cron_expression
        if data.cron_expression:
            expr = data.cron_expression.strip()
            if not croniter.is_valid(expr):
                raise AppException(
                    code="INVALID_CRON_EXPRESSION",
                    message=f"Invalid cron expression: '{expr}'",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            iter_cron = croniter(expr, now)
            next_run = iter_cron.get_next(datetime)
            if next_run.tzinfo is None:
                next_run = next_run.replace(tzinfo=timezone.utc)
            
            sched_job = ScheduledJob(
                id=str(uuid.uuid4()),
                queue_id=queue_id,
                job_type=data.job_type.strip(),
                payload=data.payload or {},
                cron_expression=expr,
                next_run_at=next_run,
                enabled=True,
                created_at=now,
            )
            db.add(sched_job)

        await db.commit()
        return job

    @staticmethod
    async def create_batch_jobs(
        db: AsyncSession,
        queue_id: str,
        batch_data: JobBatchCreate,
    ) -> List[Job]:
        stmt_q = (
            select(Queue)
            .where(Queue.id == queue_id)
            .options(selectinload(Queue.retry_policy))
        )
        res_q = await db.execute(stmt_q)
        queue = res_q.scalar_one_or_none()
        if not queue:
            raise AppException(
                code="QUEUE_NOT_FOUND",
                message=f"Queue with ID {queue_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        now = utcnow()
        created_jobs: List[Job] = []

        for item in batch_data.jobs:
            available_at = now
            initial_status = "QUEUED"

            if item.delay_seconds is not None and item.delay_seconds > 0:
                available_at = now + timedelta(seconds=item.delay_seconds)
                initial_status = "SCHEDULED"
            elif item.scheduled_at is not None:
                sched = item.scheduled_at
                if sched.tzinfo is None:
                    sched = sched.replace(tzinfo=timezone.utc)
                available_at = sched
                if available_at > now:
                    initial_status = "SCHEDULED"

            max_attempts = item.max_attempts or (queue.retry_policy.max_attempts if queue.retry_policy else 3)

            job_id = str(uuid.uuid4())
            job = Job(
                id=job_id,
                queue_id=queue_id,
                job_type=item.job_type.strip(),
                payload=item.payload or {},
                status=initial_status,
                priority=item.priority,
                scheduled_at=item.scheduled_at,
                available_at=available_at,
                attempts=0,
                max_attempts=max_attempts,
                created_at=now,
                updated_at=now,
            )
            db.add(job)

            log_entry = JobLog(
                id=str(uuid.uuid4()),
                job_id=job_id,
                level="INFO",
                message=f"Batch created job with status={initial_status}",
                timestamp=now,
            )
            db.add(log_entry)
            created_jobs.append(job)

        await db.commit()
        return created_jobs

    @staticmethod
    async def get_job(db: AsyncSession, job_id: str) -> Job:
        stmt = (
            select(Job)
            .where(Job.id == job_id)
            .options(
                selectinload(Job.queue),
                selectinload(Job.executions),
                selectinload(Job.logs),
                selectinload(Job.dead_letter_entry),
            )
        )
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            raise AppException(
                code="JOB_NOT_FOUND",
                message=f"Job with ID {job_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return job

    @staticmethod
    async def list_jobs(
        db: AsyncSession,
        queue_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        job_type: Optional[str] = None,
        priority: Optional[int] = None,
        worker_id: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Job], int]:
        stmt = select(Job).options(selectinload(Job.queue))
        count_stmt = select(func.count(Job.id))

        filters = []
        if queue_id:
            filters.append(Job.queue_id == queue_id)
        if status_filter:
            filters.append(Job.status == status_filter.upper())
        if job_type:
            filters.append(Job.job_type == job_type)
        if priority is not None:
            filters.append(Job.priority == priority)
        if created_after:
            filters.append(Job.created_at >= created_after)
        if created_before:
            filters.append(Job.created_at <= created_before)
        if worker_id:
            stmt = stmt.join(JobExecution, Job.id == JobExecution.job_id).where(JobExecution.worker_id == worker_id)
            count_stmt = count_stmt.join(JobExecution, Job.id == JobExecution.job_id).where(JobExecution.worker_id == worker_id)

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        # Order by priority desc, created_at desc
        stmt = stmt.order_by(Job.priority.desc(), Job.created_at.desc())

        # Total count
        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one() or 0

        # Pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        res = await db.execute(stmt)
        jobs = list(res.scalars().all())

        return jobs, total

    @staticmethod
    async def retry_dead_letter_job(db: AsyncSession, job_id: str) -> Job:
        job = await JobService.get_job(db, job_id)
        if job.status not in ("DEAD_LETTER", "FAILED"):
            raise AppException(
                code="INVALID_STATE",
                message=f"Job is in state '{job.status}'. Only DEAD_LETTER or FAILED jobs can be retried.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        now = utcnow()
        job.status = "QUEUED"
        job.available_at = now
        job.updated_at = now
        # Give another set of attempts or reset attempts
        job.attempts = 0

        # Remove dead letter entry if present
        await db.execute(delete(DeadLetterJob).where(DeadLetterJob.job_id == job.id))
        job.dead_letter_entry = None

        # Record manual retry log
        log_entry = JobLog(
            id=str(uuid.uuid4()),
            job_id=job.id,
            level="INFO",
            message="Job manually requeued from Dead Letter Queue / Failed state",
            timestamp=now,
        )
        db.add(log_entry)

        await db.commit()
        return await JobService.get_job(db, job_id)

    @staticmethod
    async def get_dead_letter_jobs(
        db: AsyncSession,
        queue_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Job], int]:
        stmt = (
            select(Job)
            .where(Job.status == "DEAD_LETTER")
            .options(
                selectinload(Job.queue),
                selectinload(Job.dead_letter_entry),
            )
        )
        count_stmt = select(func.count(Job.id)).where(Job.status == "DEAD_LETTER")

        if queue_id:
            stmt = stmt.where(Job.queue_id == queue_id)
            count_stmt = count_stmt.where(Job.queue_id == queue_id)

        stmt = stmt.order_by(Job.updated_at.desc())

        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one() or 0

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        res = await db.execute(stmt)
        return list(res.scalars().all()), total

    @staticmethod
    async def get_job_executions(db: AsyncSession, job_id: str) -> List[JobExecution]:
        stmt = (
            select(JobExecution)
            .where(JobExecution.job_id == job_id)
            .order_by(JobExecution.attempt_number.desc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_job_logs(db: AsyncSession, job_id: str) -> List[JobLog]:
        stmt = (
            select(JobLog)
            .where(JobLog.job_id == job_id)
            .order_by(JobLog.timestamp.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


job_service = JobService()

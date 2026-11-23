import asyncio
import logging
import os
import signal
import socket
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Set, Dict, Any, Optional

from croniter import croniter
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, update, func, and_
from sqlalchemy.orm import selectinload

# Add project roots to path if necessary
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.database import Base
from app.models.project import Queue, RetryPolicy
from app.models.job import Job, JobExecution, JobLog, ScheduledJob, DeadLetterJob
from app.services.worker_service import worker_service
from app.services.job_service import job_service
from executor import ExecutorRegistry
from heartbeat import HeartbeatManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
)
logger = logging.getLogger("scheduler.worker")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DistributedWorker:
    def __init__(
        self,
        worker_id: Optional[str] = None,
        worker_name: Optional[str] = None,
        concurrency: int = 5,
        poll_interval: float = 1.0,
        heartbeat_interval: float = 5.0,
        stale_timeout: float = 15.0,
        db_url: Optional[str] = None,
    ):
        self.worker_id = worker_id or str(uuid.uuid4())
        self.worker_name = worker_name or os.getenv("WORKER_NAME", f"worker-{socket.gethostname()}-{self.worker_id[:8]}")
        self.hostname = socket.gethostname()
        self.concurrency = int(os.getenv("WORKER_CONCURRENCY", str(concurrency)))
        self.poll_interval = float(os.getenv("POLL_INTERVAL_SECONDS", str(poll_interval)))
        self.heartbeat_interval = float(os.getenv("HEARTBEAT_INTERVAL_SECONDS", str(heartbeat_interval)))
        self.stale_timeout = float(os.getenv("STALE_WORKER_TIMEOUT_SECONDS", str(stale_timeout)))

        resolved_db_url = db_url or settings.DATABASE_URL
        if resolved_db_url.startswith("sqlite:///"):
            resolved_db_url = resolved_db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif resolved_db_url.startswith("postgresql://"):
            resolved_db_url = resolved_db_url.replace("postgresql://", "postgresql+asyncpg://")

        self.engine = create_async_engine(
            resolved_db_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        self._active_tasks: Set[asyncio.Task] = set()
        self._running = False
        self._stopping = False
        self._stop_event = asyncio.Event()

        self.heartbeat_mgr = HeartbeatManager(
            worker_id=self.worker_id,
            session_factory=self.session_factory,
            interval_seconds=self.heartbeat_interval,
            stale_timeout_seconds=self.stale_timeout,
            get_active_jobs_count=lambda: len(self._active_tasks),
            get_available_slots=lambda: max(0, self.concurrency - len(self._active_tasks)),
        )

    async def start(self):
        self._running = True
        logger.info(f"Starting worker '{self.worker_name}' (ID: {self.worker_id}, Concurrency: {self.concurrency})")

        # Register in database
        async with self.session_factory() as session:
            await worker_service.register_worker(
                db=session,
                worker_id=self.worker_id,
                worker_name=self.worker_name,
                hostname=self.hostname,
                concurrency=self.concurrency,
            )

        # Start heartbeat
        await self.heartbeat_mgr.start()

        # Start background scheduler loop for recurring cron jobs
        scheduler_task = asyncio.create_task(self._scheduler_loop())

        # Main polling loop
        try:
            while self._running and not self._stopping:
                await self._poll_and_dispatch()
                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            pass
        finally:
            scheduler_task.cancel()
            await self._shutdown()

    async def _poll_and_dispatch(self):
        available_slots = max(0, self.concurrency - len(self._active_tasks))
        if available_slots <= 0:
            return

        try:
            async with self.session_factory() as session:
                # 1. Fetch active (non-paused) queues ordered by priority desc
                q_stmt = select(Queue).where(Queue.paused == False).order_by(Queue.priority.desc())
                q_res = await session.execute(q_stmt)
                queues = list(q_res.scalars().all())

                if not queues:
                    return

                for queue in queues:
                    if available_slots <= 0:
                        break

                    # 2. Check active jobs count in this queue to enforce queue concurrency limit
                    active_in_q_stmt = select(func.count(Job.id)).where(
                        Job.queue_id == queue.id,
                        Job.status.in_(["CLAIMED", "RUNNING"]),
                    )
                    active_q_res = await session.execute(active_in_q_stmt)
                    active_in_q = active_q_res.scalar_one() or 0

                    if active_in_q >= queue.concurrency_limit:
                        continue  # Queue concurrency reached, skip to next queue

                    slots_for_queue = min(available_slots, queue.concurrency_limit - active_in_q)
                    if slots_for_queue <= 0:
                        continue

                    # 3. ATOMIC CLAIMING QUERY: SELECT ... FOR UPDATE SKIP LOCKED
                    now = utcnow()
                    claim_stmt = (
                        select(Job)
                        .where(
                            Job.queue_id == queue.id,
                            Job.status.in_(["QUEUED", "RETRYING"]),
                            Job.available_at <= now,
                        )
                        .order_by(Job.priority.desc(), Job.available_at.asc())
                        .limit(slots_for_queue)
                    )

                    # Apply FOR UPDATE SKIP LOCKED on engines supporting row locking
                    if self.engine.dialect.name == "postgresql":
                        claim_stmt = claim_stmt.with_for_update(skip_locked=True)

                    claim_res = await session.execute(claim_stmt)
                    claimed_jobs = list(claim_res.scalars().all())

                    if not claimed_jobs:
                        continue

                    # 4. Update status to CLAIMED & create JobExecution records in the same transaction
                    dispatched_items = []
                    for job in claimed_jobs:
                        job.status = "CLAIMED"
                        job.attempts += 1
                        job.updated_at = now

                        execution_id = str(uuid.uuid4())
                        execution = JobExecution(
                            id=execution_id,
                            job_id=job.id,
                            worker_id=self.worker_id,
                            attempt_number=job.attempts,
                            status="RUNNING",
                            started_at=now,
                        )
                        session.add(execution)

                        log_entry = JobLog(
                            id=str(uuid.uuid4()),
                            job_id=job.id,
                            execution_id=execution_id,
                            level="INFO",
                            message=f"Job claimed by worker '{self.worker_name}' (attempt #{job.attempts})",
                            timestamp=now,
                        )
                        session.add(log_entry)

                        dispatched_items.append((
                            job.id,
                            job.queue_id,
                            execution_id,
                            job.job_type,
                            job.payload,
                            job.attempts,
                            job.max_attempts,
                        ))

                    # Commit claiming transaction immediately before execution begins!
                    await session.commit()
                    logger.info(f"Worker '{self.worker_name}' atomically claimed {len(dispatched_items)} job(s) from queue '{queue.name}'")

                    # 5. Dispatch async execution tasks
                    for item in dispatched_items:
                        task = asyncio.create_task(self._execute_job(*item))
                        self._active_tasks.add(task)
                        task.add_done_callback(self._active_tasks.discard)
                        available_slots -= 1

        except Exception as e:
            logger.error(f"Error during poll & claim: {e}", exc_info=True)

    async def _execute_job(
        self,
        job_id: str,
        queue_id: str,
        execution_id: str,
        job_type: str,
        payload: Dict[str, Any],
        attempt_number: int,
        max_attempts: int,
    ):
        """Executes a single claimed job in a dedicated asyncio task."""
        start_time = time.perf_counter()
        start_dt = utcnow()

        # Update job to RUNNING
        async with self.session_factory() as session:
            await session.execute(
                update(Job).where(Job.id == job_id).values(status="RUNNING", updated_at=start_dt)
            )
            await session.commit()

        # Helper logging function for executors
        async def log_fn(level: str, message: str):
            try:
                async with self.session_factory() as s:
                    log_rec = JobLog(
                        id=str(uuid.uuid4()),
                        job_id=job_id,
                        execution_id=execution_id,
                        level=level.upper(),
                        message=message,
                        timestamp=utcnow(),
                    )
                    s.add(log_rec)
                    await s.commit()
            except Exception as le:
                logger.error(f"Failed to record job log: {le}")

        executor = ExecutorRegistry.get(job_type)
        success = False
        error_msg: Optional[str] = None
        result_payload: Optional[Dict[str, Any]] = None

        try:
            result_payload = await executor.execute(payload, log_fn, attempt_number)
            success = True
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Job {job_id} ({job_type}) failed on attempt #{attempt_number}: {error_msg}")

        end_dt = utcnow()
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Record completion / failure in database
        async with self.session_factory() as session:
            try:
                if success:
                    # 1. Update Execution
                    await session.execute(
                        update(JobExecution)
                        .where(JobExecution.id == execution_id)
                        .values(
                            status="COMPLETED",
                            completed_at=end_dt,
                            duration_ms=duration_ms,
                            error_message=None,
                        )
                    )
                    # 2. Update Job
                    await session.execute(
                        update(Job)
                        .where(Job.id == job_id)
                        .values(
                            status="COMPLETED",
                            completed_at=end_dt,
                            updated_at=end_dt,
                        )
                    )
                    # 3. Log
                    session.add(
                        JobLog(
                            id=str(uuid.uuid4()),
                            job_id=job_id,
                            execution_id=execution_id,
                            level="INFO",
                            message=f"Job completed successfully in {duration_ms}ms",
                            timestamp=end_dt,
                        )
                    )
                    logger.info(f"Job {job_id} COMPLETED in {duration_ms}ms")

                else:
                    # Job Failed: Record execution failure
                    await session.execute(
                        update(JobExecution)
                        .where(JobExecution.id == execution_id)
                        .values(
                            status="FAILED",
                            completed_at=end_dt,
                            duration_ms=duration_ms,
                            error_message=error_msg,
                        )
                    )

                    # Fetch Queue & Retry Policy
                    q_stmt = select(Queue).where(Queue.id == queue_id).options(selectinload(Queue.retry_policy))
                    q_res = await session.execute(q_stmt)
                    queue_obj = q_res.scalar_one_or_none()

                    strategy = "exponential"
                    initial_delay = 5
                    multiplier = 2.0
                    if queue_obj and queue_obj.retry_policy:
                        strategy = queue_obj.retry_policy.strategy
                        initial_delay = queue_obj.retry_policy.initial_delay_seconds
                        multiplier = queue_obj.retry_policy.backoff_multiplier

                    if attempt_number < max_attempts:
                        # Schedule Retry
                        delay_secs = job_service.calculate_retry_delay(
                            strategy=strategy,
                            attempt=attempt_number,
                            initial_delay=initial_delay,
                            multiplier=multiplier,
                        )
                        next_available = end_dt + timedelta(seconds=delay_secs)

                        await session.execute(
                            update(Job)
                            .where(Job.id == job_id)
                            .values(
                                status="RETRYING",
                                available_at=next_available,
                                updated_at=end_dt,
                            )
                        )
                        session.add(
                            JobLog(
                                id=str(uuid.uuid4()),
                                job_id=job_id,
                                execution_id=execution_id,
                                level="WARN",
                                message=f"Job failed (attempt {attempt_number}/{max_attempts}). Retrying in {delay_secs}s at {next_available.isoformat()}: {error_msg}",
                                timestamp=end_dt,
                            )
                        )
                        logger.info(f"Job {job_id} scheduled for RETRY in {delay_secs}s (attempt {attempt_number}/{max_attempts})")

                    else:
                        # Exhausted retries -> DEAD_LETTER QUEUE
                        await session.execute(
                            update(Job)
                            .where(Job.id == job_id)
                            .values(
                                status="DEAD_LETTER",
                                updated_at=end_dt,
                            )
                        )
                        dlq_entry = DeadLetterJob(
                            id=str(uuid.uuid4()),
                            job_id=job_id,
                            reason=f"Exhausted maximum retry attempts ({max_attempts})",
                            final_error=error_msg,
                            failed_at=end_dt,
                            retry_count=attempt_number,
                        )
                        session.add(dlq_entry)

                        session.add(
                            JobLog(
                                id=str(uuid.uuid4()),
                                job_id=job_id,
                                execution_id=execution_id,
                                level="ERROR",
                                message=f"Job permanently failed after {max_attempts} attempts. Moved to Dead Letter Queue: {error_msg}",
                                timestamp=end_dt,
                            )
                        )
                        logger.error(f"Job {job_id} moved to DEAD_LETTER after {max_attempts} attempts: {error_msg}")

                await session.commit()

            except Exception as pe:
                logger.error(f"Failed to record completion/failure for job {job_id}: {pe}", exc_info=True)
                await session.rollback()

    async def _scheduler_loop(self):
        """Polls scheduled_jobs table and triggers recurring cron instances."""
        while self._running and not self._stopping:
            try:
                now = utcnow()
                async with self.session_factory() as session:
                    stmt = select(ScheduledJob).where(
                        ScheduledJob.enabled == True,
                        ScheduledJob.next_run_at <= now,
                    )
                    res = await session.execute(stmt)
                    due_schedules = list(res.scalars().all())

                    for sched in due_schedules:
                        # 1. Enqueue job
                        job_id = str(uuid.uuid4())
                        new_job = Job(
                            id=job_id,
                            queue_id=sched.queue_id,
                            job_type=sched.job_type,
                            payload=sched.payload or {},
                            status="QUEUED",
                            priority=0,
                            available_at=now,
                            attempts=0,
                            max_attempts=3,
                            created_at=now,
                            updated_at=now,
                        )
                        session.add(new_job)

                        session.add(
                            JobLog(
                                id=str(uuid.uuid4()),
                                job_id=job_id,
                                level="INFO",
                                message=f"Triggered by cron schedule ({sched.cron_expression})",
                                timestamp=now,
                            )
                        )

                        # 2. Compute next run time
                        iter_cron = croniter(sched.cron_expression, now)
                        next_dt = iter_cron.get_next(datetime)
                        if next_dt.tzinfo is None:
                            next_dt = next_dt.replace(tzinfo=timezone.utc)
                        sched.next_run_at = next_dt

                    if due_schedules:
                        await session.commit()
                        logger.info(f"Triggered {len(due_schedules)} recurring scheduled job(s)")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)

            try:
                await asyncio.sleep(5.0)
            except asyncio.CancelledError:
                break

    async def _shutdown(self):
        """Gracefully shuts down the worker daemon, draining running jobs."""
        logger.info(f"Initiating graceful shutdown for worker '{self.worker_name}'...")
        self._stopping = True

        # 1. Update status to STOPPING
        try:
            async with self.session_factory() as session:
                await worker_service.set_worker_stopping(session, self.worker_id)
        except Exception as e:
            logger.error(f"Failed to update status to STOPPING: {e}")

        # 2. Stop heartbeat manager
        await self.heartbeat_mgr.stop()

        # 3. Await running tasks with timeout
        if self._active_tasks:
            logger.info(f"Waiting for {len(self._active_tasks)} active job(s) to finish...")
            done, pending = await asyncio.wait(self._active_tasks, timeout=30.0)
            if pending:
                logger.warning(f"Cancelling {len(pending)} remaining in-flight job(s) after timeout")
                for t in pending:
                    t.cancel()

        # 4. Mark worker OFFLINE
        try:
            async with self.session_factory() as session:
                await worker_service.set_worker_offline(session, self.worker_id)
        except Exception as e:
            logger.error(f"Failed to update status to OFFLINE: {e}")

        # 5. Dispose DB Engine
        await self.engine.dispose()
        logger.info(f"Worker '{self.worker_name}' shut down cleanly.")

    def stop(self):
        self._stopping = True
        self._running = False


async def run_worker():
    worker = DistributedWorker()

    loop = asyncio.get_running_loop()

    # Graceful shutdown handler for signals
    def signal_handler():
        logger.info("Shutdown signal received!")
        worker.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Signal handlers not implemented on Windows event loops
            signal.signal(sig, lambda s, f: signal_handler())

    await worker.start()


if __name__ == "__main__":
    asyncio.run(run_worker())

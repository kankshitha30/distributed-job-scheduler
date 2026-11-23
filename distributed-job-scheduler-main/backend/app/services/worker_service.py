import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc, and_
from sqlalchemy.orm import selectinload
from fastapi import status

from app.models.worker import Worker, WorkerHeartbeat
from app.schemas.worker import WorkerResponse, WorkerHeartbeatResponse
from app.middleware.error_handler import AppException
from app.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkerService:
    @staticmethod
    async def register_worker(
        db: AsyncSession,
        worker_id: str,
        worker_name: str,
        hostname: str,
        concurrency: int = 5,
    ) -> Worker:
        now = utcnow()
        stmt = select(Worker).where(Worker.id == worker_id)
        res = await db.execute(stmt)
        worker = res.scalar_one_or_none()

        if worker:
            worker.worker_name = worker_name
            worker.hostname = hostname
            worker.status = "ONLINE"
            worker.concurrency = concurrency
            worker.last_heartbeat = now
            worker.stopped_at = None
        else:
            worker = Worker(
                id=worker_id,
                worker_name=worker_name,
                hostname=hostname,
                status="ONLINE",
                concurrency=concurrency,
                last_heartbeat=now,
                started_at=now,
            )
            db.add(worker)

        # Initial heartbeat
        hb = WorkerHeartbeat(
            id=str(uuid.uuid4()),
            worker_id=worker_id,
            heartbeat_at=now,
            active_jobs=0,
            available_slots=concurrency,
        )
        db.add(hb)

        await db.commit()
        return worker

    @staticmethod
    async def record_heartbeat(
        db: AsyncSession,
        worker_id: str,
        active_jobs: int,
        available_slots: int,
    ) -> None:
        now = utcnow()
        # Update worker record
        await db.execute(
            update(Worker)
            .where(Worker.id == worker_id)
            .values(last_heartbeat=now, status="ONLINE")
        )
        # Add heartbeat record
        hb = WorkerHeartbeat(
            id=str(uuid.uuid4()),
            worker_id=worker_id,
            heartbeat_at=now,
            active_jobs=active_jobs,
            available_slots=available_slots,
        )
        db.add(hb)
        await db.commit()

    @staticmethod
    async def set_worker_stopping(db: AsyncSession, worker_id: str) -> None:
        now = utcnow()
        await db.execute(
            update(Worker)
            .where(Worker.id == worker_id)
            .values(status="STOPPING", last_heartbeat=now)
        )
        await db.commit()

    @staticmethod
    async def set_worker_offline(db: AsyncSession, worker_id: str) -> None:
        now = utcnow()
        await db.execute(
            update(Worker)
            .where(Worker.id == worker_id)
            .values(status="OFFLINE", stopped_at=now, last_heartbeat=now)
        )
        await db.commit()

    @staticmethod
    async def mark_stale_workers(
        db: AsyncSession,
        timeout_seconds: float = 15.0,
    ) -> int:
        now = utcnow()
        threshold = now - timedelta(seconds=timeout_seconds)
        stmt = (
            update(Worker)
            .where(
                Worker.status == "ONLINE",
                Worker.last_heartbeat < threshold,
            )
            .values(status="OFFLINE")
        )
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount

    @staticmethod
    async def list_workers(db: AsyncSession) -> List[WorkerResponse]:
        # Run stale check
        await WorkerService.mark_stale_workers(db, settings.STALE_WORKER_TIMEOUT_SECONDS)

        stmt = (
            select(Worker)
            .options(selectinload(Worker.heartbeats))
            .order_by(Worker.started_at.desc())
        )
        res = await db.execute(stmt)
        workers = list(res.scalars().all())

        now = utcnow()
        results = []
        for w in workers:
            latest_hb = w.heartbeats[0] if w.heartbeats else None
            active_jobs = latest_hb.active_jobs if latest_hb else 0
            available_slots = latest_hb.available_slots if latest_hb else w.concurrency
            
            # Handle tz-awareness comparison
            last_hb = w.last_heartbeat
            if last_hb.tzinfo is None:
                last_hb = last_hb.replace(tzinfo=timezone.utc)
            
            is_stale = (now - last_hb).total_seconds() > settings.STALE_WORKER_TIMEOUT_SECONDS
            status_val = "OFFLINE" if is_stale and w.status == "ONLINE" else w.status

            results.append(
                WorkerResponse(
                    id=w.id,
                    worker_name=w.worker_name,
                    hostname=w.hostname,
                    status=status_val,
                    concurrency=w.concurrency,
                    last_heartbeat=w.last_heartbeat,
                    started_at=w.started_at,
                    stopped_at=w.stopped_at,
                    active_jobs=active_jobs if status_val == "ONLINE" else 0,
                    available_slots=available_slots if status_val == "ONLINE" else 0,
                    is_stale=is_stale,
                )
            )
        return results

    @staticmethod
    async def get_worker(db: AsyncSession, worker_id: str) -> WorkerResponse:
        await WorkerService.mark_stale_workers(db, settings.STALE_WORKER_TIMEOUT_SECONDS)

        stmt = (
            select(Worker)
            .where(Worker.id == worker_id)
            .options(selectinload(Worker.heartbeats))
        )
        res = await db.execute(stmt)
        w = res.scalar_one_or_none()
        if not w:
            raise AppException(
                code="WORKER_NOT_FOUND",
                message=f"Worker with ID {worker_id} does not exist",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        now = utcnow()
        latest_hb = w.heartbeats[0] if w.heartbeats else None
        active_jobs = latest_hb.active_jobs if latest_hb else 0
        available_slots = latest_hb.available_slots if latest_hb else w.concurrency

        last_hb = w.last_heartbeat
        if last_hb.tzinfo is None:
            last_hb = last_hb.replace(tzinfo=timezone.utc)

        is_stale = (now - last_hb).total_seconds() > settings.STALE_WORKER_TIMEOUT_SECONDS
        status_val = "OFFLINE" if is_stale and w.status == "ONLINE" else w.status

        return WorkerResponse(
            id=w.id,
            worker_name=w.worker_name,
            hostname=w.hostname,
            status=status_val,
            concurrency=w.concurrency,
            last_heartbeat=w.last_heartbeat,
            started_at=w.started_at,
            stopped_at=w.stopped_at,
            active_jobs=active_jobs if status_val == "ONLINE" else 0,
            available_slots=available_slots if status_val == "ONLINE" else 0,
            is_stale=is_stale,
        )

    @staticmethod
    async def get_heartbeats(
        db: AsyncSession,
        worker_id: str,
        limit: int = 50,
    ) -> List[WorkerHeartbeat]:
        stmt = (
            select(WorkerHeartbeat)
            .where(WorkerHeartbeat.worker_id == worker_id)
            .order_by(WorkerHeartbeat.heartbeat_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


worker_service = WorkerService()

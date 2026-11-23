import asyncio
import logging
from typing import Callable
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.services.worker_service import worker_service

logger = logging.getLogger("scheduler.worker.heartbeat")


class HeartbeatManager:
    def __init__(
        self,
        worker_id: str,
        session_factory: async_sessionmaker[AsyncSession],
        interval_seconds: float = 5.0,
        stale_timeout_seconds: float = 15.0,
        get_active_jobs_count: Callable[[], int] = lambda: 0,
        get_available_slots: Callable[[], int] = lambda: 5,
    ):
        self.worker_id = worker_id
        self.session_factory = session_factory
        self.interval_seconds = interval_seconds
        self.stale_timeout_seconds = stale_timeout_seconds
        self.get_active_jobs_count = get_active_jobs_count
        self.get_available_slots = get_available_slots
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Heartbeat manager started for worker {self.worker_id} (interval={self.interval_seconds}s)")

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Heartbeat manager stopped for worker {self.worker_id}")

    async def _heartbeat_loop(self):
        while self._running:
            try:
                active_jobs = self.get_active_jobs_count()
                available_slots = self.get_available_slots()

                async with self.session_factory() as session:
                    # 1. Update own heartbeat
                    await worker_service.record_heartbeat(
                        db=session,
                        worker_id=self.worker_id,
                        active_jobs=active_jobs,
                        available_slots=available_slots,
                    )
                    # 2. Mark any other stale workers offline
                    await worker_service.mark_stale_workers(
                        db=session,
                        timeout_seconds=self.stale_timeout_seconds,
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error during heartbeat tick: {e}", exc_info=True)

            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

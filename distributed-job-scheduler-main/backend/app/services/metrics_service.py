from datetime import datetime, timezone, timedelta
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.project import Queue
from app.models.job import Job, JobExecution
from app.models.worker import Worker
from app.schemas.metrics import OverviewMetricsResponse, MetricTimeSeriesPoint
from app.services.worker_service import worker_service
from app.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MetricsService:
    @staticmethod
    async def get_overview(db: AsyncSession) -> OverviewMetricsResponse:
        # 1. Total queues
        q_res = await db.execute(select(func.count(Queue.id)))
        total_queues = q_res.scalar_one() or 0

        # 2. Job counts by status
        job_status_stmt = select(Job.status, func.count(Job.id)).group_by(Job.status)
        js_res = await db.execute(job_status_stmt)
        counts = {status: count for status, count in js_res.all()}

        total_jobs = sum(counts.values())
        queued_jobs = counts.get("QUEUED", 0) + counts.get("SCHEDULED", 0)
        running_jobs = counts.get("RUNNING", 0) + counts.get("CLAIMED", 0)
        completed_jobs = counts.get("COMPLETED", 0)
        failed_jobs = counts.get("FAILED", 0)
        retrying_jobs = counts.get("RETRYING", 0)
        dead_letter_jobs = counts.get("DEAD_LETTER", 0)

        # 3. Active & Total Workers
        await worker_service.mark_stale_workers(db, settings.STALE_WORKER_TIMEOUT_SECONDS)
        w_res = await db.execute(select(Worker.status, func.count(Worker.id)).group_by(Worker.status))
        w_counts = {status: count for status, count in w_res.all()}
        active_workers = w_counts.get("ONLINE", 0)
        total_workers = sum(w_counts.values())

        # 4. Average execution time
        avg_res = await db.execute(
            select(func.avg(JobExecution.duration_ms)).where(
                JobExecution.status == "COMPLETED",
                JobExecution.duration_ms.is_not(None),
            )
        )
        avg_duration = avg_res.scalar_one_or_none() or 0.0

        # 5. Success rate
        finished = completed_jobs + failed_jobs + dead_letter_jobs
        success_rate = (completed_jobs / finished * 100.0) if finished > 0 else 100.0

        # 6. Throughput (jobs completed in last 10 minutes)
        now = utcnow()
        ten_mins_ago = now - timedelta(minutes=10)
        tp_res = await db.execute(
            select(func.count(JobExecution.id)).where(
                JobExecution.status == "COMPLETED",
                JobExecution.completed_at >= ten_mins_ago,
            )
        )
        recent_completed = tp_res.scalar_one_or_none() or 0
        throughput_per_min = round(recent_completed / 10.0, 2)

        # 7. Job type distribution
        jt_res = await db.execute(select(Job.job_type, func.count(Job.id)).group_by(Job.job_type))
        job_type_dist = {jt: count for jt, count in jt_res.all()}

        # 8. Time series generation (last 6 10-minute buckets)
        time_series: List[MetricTimeSeriesPoint] = []
        for i in range(6, -1, -1):
            bucket_start = now - timedelta(minutes=(i + 1) * 10)
            bucket_end = now - timedelta(minutes=i * 10)
            bucket_label = bucket_end.strftime("%H:%M")

            # Completed in window
            c_res = await db.execute(
                select(func.count(JobExecution.id)).where(
                    JobExecution.status == "COMPLETED",
                    JobExecution.completed_at >= bucket_start,
                    JobExecution.completed_at < bucket_end,
                )
            )
            c_count = c_res.scalar_one_or_none() or 0

            # Failed in window
            f_res = await db.execute(
                select(func.count(JobExecution.id)).where(
                    JobExecution.status == "FAILED",
                    JobExecution.completed_at >= bucket_start,
                    JobExecution.completed_at < bucket_end,
                )
            )
            f_count = f_res.scalar_one_or_none() or 0

            # Queued in window
            q_count_res = await db.execute(
                select(func.count(Job.id)).where(
                    Job.created_at >= bucket_start,
                    Job.created_at < bucket_end,
                )
            )
            q_count = q_count_res.scalar_one_or_none() or 0

            time_series.append(
                MetricTimeSeriesPoint(
                    timestamp=bucket_label,
                    completed=c_count,
                    failed=f_count,
                    queued=q_count,
                )
            )

        return OverviewMetricsResponse(
            total_queues=total_queues,
            total_jobs=total_jobs,
            queued_jobs=queued_jobs,
            running_jobs=running_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            retrying_jobs=retrying_jobs,
            dead_letter_jobs=dead_letter_jobs,
            active_workers=active_workers,
            total_workers=total_workers,
            throughput_per_minute=throughput_per_min,
            success_rate=round(float(success_rate), 2),
            average_duration_ms=round(float(avg_duration), 2),
            time_series=time_series,
            job_type_distribution=job_type_dist,
        )


metrics_service = MetricsService()

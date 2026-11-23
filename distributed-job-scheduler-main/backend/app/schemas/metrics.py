from typing import List, Dict, Any
from pydantic import BaseModel


class MetricTimeSeriesPoint(BaseModel):
    timestamp: str
    completed: int = 0
    failed: int = 0
    queued: int = 0


class OverviewMetricsResponse(BaseModel):
    total_queues: int = 0
    total_jobs: int = 0
    queued_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    retrying_jobs: int = 0
    dead_letter_jobs: int = 0
    active_workers: int = 0
    total_workers: int = 0
    throughput_per_minute: float = 0.0
    success_rate: float = 0.0
    average_duration_ms: float = 0.0
    time_series: List[MetricTimeSeriesPoint] = []
    job_type_distribution: Dict[str, int] = {}

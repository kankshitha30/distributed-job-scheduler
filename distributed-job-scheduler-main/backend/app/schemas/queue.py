from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.retry_policy import RetryPolicyResponse


class QueueBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    priority: int = Field(default=0, ge=0, le=100)
    concurrency_limit: int = Field(default=5, ge=1, le=1000)
    retry_policy_id: Optional[str] = None


class QueueCreate(QueueBase):
    project_id: Optional[str] = None


class QueueUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    priority: Optional[int] = Field(default=None, ge=0, le=100)
    concurrency_limit: Optional[int] = Field(default=None, ge=1, le=1000)
    retry_policy_id: Optional[str] = None
    paused: Optional[bool] = None


class QueueStats(BaseModel):
    total_jobs: int = 0
    queued_jobs: int = 0
    running_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    retrying_jobs: int = 0
    dead_letter_jobs: int = 0
    average_execution_time_ms: float = 0.0
    success_rate: float = 0.0


class QueueResponse(QueueBase):
    id: str
    project_id: str
    paused: bool
    created_at: datetime
    updated_at: datetime
    retry_policy: Optional[RetryPolicyResponse] = None
    stats: Optional[QueueStats] = None

    class Config:
        from_attributes = True

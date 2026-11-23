from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.schemas.execution import JobExecutionResponse, JobLogResponse


class JobCreate(BaseModel):
    job_type: str = Field(..., min_length=1, max_length=100)
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=100)
    delay_seconds: Optional[int] = Field(default=None, ge=0)
    scheduled_at: Optional[datetime] = None
    cron_expression: Optional[str] = None
    max_attempts: Optional[int] = Field(default=None, ge=1, le=20)


class JobBatchCreate(BaseModel):
    jobs: List[JobCreate] = Field(..., min_length=1, max_length=100)


class DeadLetterResponse(BaseModel):
    id: str
    job_id: str
    reason: str
    final_error: Optional[str] = None
    failed_at: datetime
    retry_count: int

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    id: str
    queue_id: str
    queue_name: Optional[str] = None
    job_type: str
    payload: Dict[str, Any]
    status: str
    priority: int
    scheduled_at: Optional[datetime] = None
    available_at: datetime
    attempts: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobDetailResponse(JobResponse):
    executions: List[JobExecutionResponse] = []
    logs: List[JobLogResponse] = []
    dead_letter: Optional[DeadLetterResponse] = None

    class Config:
        from_attributes = True

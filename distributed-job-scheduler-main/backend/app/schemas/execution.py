from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class JobLogResponse(BaseModel):
    id: str
    job_id: str
    execution_id: Optional[str] = None
    level: str
    message: str
    timestamp: datetime

    class Config:
        from_attributes = True


class JobExecutionResponse(BaseModel):
    id: str
    job_id: str
    worker_id: Optional[str] = None
    attempt_number: int
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

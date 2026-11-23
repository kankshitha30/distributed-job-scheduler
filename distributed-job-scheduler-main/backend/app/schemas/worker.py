from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class WorkerHeartbeatResponse(BaseModel):
    id: str
    worker_id: str
    heartbeat_at: datetime
    active_jobs: int
    available_slots: int

    class Config:
        from_attributes = True


class WorkerResponse(BaseModel):
    id: str
    worker_name: str
    hostname: str
    status: str
    concurrency: int
    last_heartbeat: datetime
    started_at: datetime
    stopped_at: Optional[datetime] = None
    active_jobs: int = 0
    available_slots: int = 0
    is_stale: bool = False

    class Config:
        from_attributes = True

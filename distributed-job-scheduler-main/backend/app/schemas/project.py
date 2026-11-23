from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    organization_id: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    queues_count: Optional[int] = 0

    class Config:
        from_attributes = True

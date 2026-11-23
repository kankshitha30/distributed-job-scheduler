from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.worker import WorkerResponse, WorkerHeartbeatResponse
from app.services.worker_service import worker_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/workers", tags=["Workers"])


@router.get("", response_model=List[WorkerResponse])
async def list_workers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await worker_service.list_workers(db)


@router.get("/{worker_id}", response_model=WorkerResponse)
async def get_worker(
    worker_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await worker_service.get_worker(db, worker_id)


@router.get("/{worker_id}/heartbeats", response_model=List[WorkerHeartbeatResponse])
async def get_worker_heartbeats(
    worker_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    heartbeats = await worker_service.get_heartbeats(db, worker_id, limit=limit)
    return [
        WorkerHeartbeatResponse(
            id=hb.id,
            worker_id=hb.worker_id,
            heartbeat_at=hb.heartbeat_at,
            active_jobs=hb.active_jobs,
            available_slots=hb.available_slots,
        )
        for hb in heartbeats
    ]

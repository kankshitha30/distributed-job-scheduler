import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.project import RetryPolicy
from app.models.user import User
from app.schemas.retry_policy import RetryPolicyCreate, RetryPolicyResponse, RetryPolicyUpdate
from app.utils.security import get_current_user
from app.middleware.error_handler import AppException

router = APIRouter(prefix="/retry-policies", tags=["Retry Policies"])


@router.post("", response_model=RetryPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_retry_policy(
    req: RetryPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    policy = RetryPolicy(
        id=str(uuid.uuid4()),
        name=req.name.strip(),
        strategy=req.strategy,
        max_attempts=req.max_attempts,
        initial_delay_seconds=req.initial_delay_seconds,
        backoff_multiplier=req.backoff_multiplier,
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy


@router.get("", response_model=List[RetryPolicyResponse])
async def list_retry_policies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(RetryPolicy).order_by(RetryPolicy.name.asc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/{policy_id}", response_model=RetryPolicyResponse)
async def get_retry_policy(
    policy_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(RetryPolicy).where(RetryPolicy.id == policy_id)
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()
    if not policy:
        raise AppException(
            code="RETRY_POLICY_NOT_FOUND",
            message=f"Retry policy with ID {policy_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return policy

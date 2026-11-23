from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.metrics import OverviewMetricsResponse
from app.services.metrics_service import metrics_service
from app.utils.security import get_current_user

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/overview", response_model=OverviewMetricsResponse)
async def get_overview_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await metrics_service.get_overview(db)

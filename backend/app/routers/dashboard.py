from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import get_dashboard_summary

router = APIRouter(tags=["任务看板"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/api/dashboard/summary", response_model=DashboardSummaryResponse)
def read_dashboard_summary(db: DbSession) -> DashboardSummaryResponse:
    return DashboardSummaryResponse(
        message="任务看板获取成功",
        summary=get_dashboard_summary(db),
    )

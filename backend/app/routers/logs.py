from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.logs import OperationLogListResponse, OperationLogResponse
from app.services.log_service import list_operation_logs

router = APIRouter(tags=["运行日志"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/api/logs", response_model=OperationLogListResponse)
def read_logs(db: DbSession, module: str | None = None) -> OperationLogListResponse:
    return OperationLogListResponse(
        message="运行日志获取成功",
        logs=[
            OperationLogResponse.model_validate(log)
            for log in list_operation_logs(db, module=module)
        ],
    )

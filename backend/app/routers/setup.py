from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.setup import SetupCompleteRequest, SetupCompleteResponse, SetupStatusResponse
from app.services.log_service import write_operation_log
from app.services.setup_service import complete_setup, get_missing_setup_items

router = APIRouter(prefix="/api/setup", tags=["安装向导"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/status", response_model=SetupStatusResponse)
def read_setup_status(db: DbSession) -> SetupStatusResponse:
    missing_items = get_missing_setup_items(db)
    return SetupStatusResponse(
        message="安装状态获取成功",
        installed=missing_items == [],
        missing_items=missing_items,
    )


@router.post("/complete", response_model=SetupCompleteResponse)
def save_setup(payload: SetupCompleteRequest, db: DbSession) -> SetupCompleteResponse:
    complete_setup(db, payload)
    write_operation_log(
        db,
        module="setup",
        message="安装向导已完成",
        detail="首次安装向导已保存必要配置。",
    )
    return SetupCompleteResponse(message="安装向导已完成")

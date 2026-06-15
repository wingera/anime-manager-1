from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.diagnostics import DiagnosticsResponse
from app.services.diagnostics_service import run_diagnostics

router = APIRouter(prefix="/api/diagnostics", tags=["系统诊断"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=DiagnosticsResponse)
def read_diagnostics(db: DbSession) -> DiagnosticsResponse:
    return run_diagnostics(db)

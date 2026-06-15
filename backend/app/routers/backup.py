from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.backup import BackupExportResponse, BackupImportRequest, BackupImportResponse
from app.services.backup_service import export_backup, import_backup
from app.services.log_service import write_operation_log

router = APIRouter(prefix="/api/backup", tags=["备份恢复"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/export", response_model=BackupExportResponse)
def download_backup(db: DbSession) -> BackupExportResponse:
    return export_backup(db)


@router.post("/import", response_model=BackupImportResponse)
def upload_backup(payload: BackupImportRequest, db: DbSession) -> BackupImportResponse:
    import_backup(db, payload)
    write_operation_log(
        db,
        module="backup",
        message="配置备份已导入",
        detail="已导入非敏感配置。",
    )
    return BackupImportResponse(message="配置备份导入成功")

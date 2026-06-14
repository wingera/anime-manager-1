from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    DownloadFile,
    DownloadTask,
    ImportJob,
    MediaMatch,
    RenamePreview,
    SourceItem,
    SourceSite,
)
from app.schemas.dashboard import DashboardSummary
from app.schemas.logs import OperationLogResponse
from app.services.log_service import list_operation_logs


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def get_dashboard_summary(db: Session) -> DashboardSummary:
    confirmed_matches_count = int(
        db.scalar(
            select(func.count())
            .select_from(MediaMatch)
            .where(MediaMatch.status == "confirmed")
        )
        or 0
    )
    failed_imports_count = int(
        db.scalar(
            select(func.count())
            .select_from(ImportJob)
            .where(ImportJob.status == "failed")
        )
        or 0
    )
    latest_logs = [
        OperationLogResponse.model_validate(log)
        for log in list_operation_logs(db, limit=10)
    ]
    return DashboardSummary(
        sources_count=_count(db, SourceSite),
        source_items_count=_count(db, SourceItem),
        matches_count=_count(db, MediaMatch),
        confirmed_matches_count=confirmed_matches_count,
        downloads_count=_count(db, DownloadTask),
        download_files_count=_count(db, DownloadFile),
        rename_previews_count=_count(db, RenamePreview),
        imports_count=_count(db, ImportJob),
        failed_imports_count=failed_imports_count,
        latest_logs=latest_logs,
    )

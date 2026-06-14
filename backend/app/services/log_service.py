import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import OperationLog

ALLOWED_LEVELS = {"info", "warning", "error"}
MAGNET_PATTERN = re.compile(r"magnet:\?[^\s，。；]+", re.IGNORECASE)
SENSITIVE_QUERY_PATTERN = re.compile(
    r"(?i)(passkey|password|token|apikey|api_key|key|auth|secret)=([^&\s]+)"
)


def sanitize_log_detail(detail: str | None) -> str | None:
    if detail is None:
        return None
    sanitized = MAGNET_PATTERN.sub("磁力入口已脱敏", detail)
    return SENSITIVE_QUERY_PATTERN.sub(r"\1=已脱敏", sanitized)


def write_operation_log(
    db: Session,
    *,
    level: str = "info",
    module: str,
    message: str,
    detail: str | None = None,
) -> OperationLog:
    log = OperationLog(
        level=level if level in ALLOWED_LEVELS else "info",
        module=module,
        message=message,
        detail=sanitize_log_detail(detail),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_operation_logs(
    db: Session,
    *,
    module: str | None = None,
    limit: int = 200,
) -> list[OperationLog]:
    statement = select(OperationLog)
    if module:
        statement = statement.where(OperationLog.module == module)
    statement = statement.order_by(
        OperationLog.created_at.desc(),
        OperationLog.id.desc(),
    ).limit(limit)
    return list(db.scalars(statement))

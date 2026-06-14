from pydantic import BaseModel

from app.schemas.logs import OperationLogResponse


class DashboardSummary(BaseModel):
    sources_count: int
    source_items_count: int
    matches_count: int
    confirmed_matches_count: int
    downloads_count: int
    download_files_count: int
    rename_previews_count: int
    imports_count: int
    failed_imports_count: int
    latest_logs: list[OperationLogResponse]


class DashboardSummaryResponse(BaseModel):
    message: str
    summary: DashboardSummary

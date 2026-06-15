from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DownloadFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    download_task_id: int
    file_index: int
    provider_file_id: str | None
    parent_id: str | None
    name: str
    size: int
    progress: float
    priority: int
    file_type: str
    selected: bool
    analysis_score: int
    season_number: int | None
    episode_number: int | None
    created_at: datetime
    updated_at: datetime


class RenamePreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    download_file_id: int
    task_id: int | None
    file_id: str | None
    parent_id: str | None
    original_name: str
    target_name: str
    original_path: str
    target_path: str
    file_size: int
    file_type: str
    episode_number: int | None
    confidence: int
    conflict: bool
    warning_message: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class DownloadFileListResponse(BaseModel):
    message: str
    files: list[DownloadFileResponse]


class DownloadFileMessageResponse(BaseModel):
    message: str
    file: DownloadFileResponse


class DownloadFileUpdateRequest(BaseModel):
    selected: bool | None = None
    file_type: str | None = Field(
        default=None,
        pattern="^(video|subtitle|image|sample|document|other|unknown)$",
    )
    season_number: int | None = Field(default=None, ge=0)
    episode_number: int | None = Field(default=None, ge=1)


class FileAnalysisMessageResponse(BaseModel):
    message: str
    files: list[DownloadFileResponse]


class RenamePreviewListResponse(BaseModel):
    message: str
    previews: list[RenamePreviewResponse]


class SimpleMessageResponse(BaseModel):
    message: str

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    download_task_id: int
    status: str
    mode: str
    total_files: int
    completed_files: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ImportFileActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    import_job_id: int
    download_file_id: int
    source_path: str
    target_path: str
    action_type: str
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ImportRequest(BaseModel):
    mode: str = Field(default="hardlink", pattern="^(hardlink|copy)$")


class ImportJobListResponse(BaseModel):
    message: str
    imports: list[ImportJobResponse]


class ImportJobMessageResponse(BaseModel):
    message: str
    import_job: ImportJobResponse


class ImportJobDetailResponse(BaseModel):
    message: str
    import_job: ImportJobResponse
    actions: list[ImportFileActionResponse]


class ImportSimpleMessageResponse(BaseModel):
    message: str

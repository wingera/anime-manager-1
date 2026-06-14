from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OperationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: str
    module: str
    message: str
    detail: str | None
    created_at: datetime


class OperationLogListResponse(BaseModel):
    message: str
    logs: list[OperationLogResponse]

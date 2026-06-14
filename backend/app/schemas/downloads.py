from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DownloadTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_item_id: int
    source_title: str
    qbittorrent_hash: str | None
    magnet_uri: str
    save_path: str
    status: str
    progress: float
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DownloadTaskMessageResponse(BaseModel):
    message: str
    download: DownloadTaskResponse


class DownloadTaskListResponse(BaseModel):
    message: str
    downloads: list[DownloadTaskResponse]


class DownloadTaskDeleteResponse(BaseModel):
    message: str

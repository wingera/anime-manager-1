from datetime import datetime

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    id: int
    tmdb_language: str
    tmdb_region: str
    has_tmdb_api_key: bool
    qbittorrent_url: str | None
    qbittorrent_username: str | None
    has_qbittorrent_password: bool
    download_dir: str
    media_library_dir: str
    matching_threshold: int
    created_at: datetime
    updated_at: datetime


class SettingsUpdateRequest(BaseModel):
    tmdb_api_key: str | None = None
    tmdb_language: str | None = None
    tmdb_region: str | None = None
    qbittorrent_url: str | None = None
    qbittorrent_username: str | None = None
    qbittorrent_password: str | None = None
    download_dir: str | None = None
    media_library_dir: str | None = None
    matching_threshold: int | None = Field(default=None, ge=0, le=100)


class ConnectionTestResponse(BaseModel):
    success: bool
    message: str

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["webpage", "manual", "rss"]


class BackupSettings(BaseModel):
    tmdb_language: str = "zh-CN"
    tmdb_region: str = "CN"
    has_tmdb_api_key: bool = False
    qbittorrent_url: str | None = None
    qbittorrent_username: str | None = None
    has_qbittorrent_password: bool = False
    download_provider: str = "qbittorrent"
    cloud115_enabled: bool = False
    cloud115_service_url: str | None = "http://192.168.1.19:9527"
    has_cloud115_service_token: bool = False
    download_dir: str = Field(min_length=1)
    media_library_dir: str = Field(min_length=1)
    matching_threshold: int = Field(ge=0, le=100)


class BackupSource(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1)
    source_type: SourceType = "webpage"
    enabled: bool = False
    auth_note: str = ""
    fetch_interval_minutes: int = Field(default=60, ge=1)
    hash_pattern: str = ""
    title_cleanup_rules: str = ""


class BackupExportResponse(BaseModel):
    message: str
    exported_at: datetime
    settings: BackupSettings
    sources: list[BackupSource]


class BackupImportRequest(BaseModel):
    settings: BackupSettings | None = None
    sources: list[BackupSource] = []


class BackupImportResponse(BaseModel):
    message: str

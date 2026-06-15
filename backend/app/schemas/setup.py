from pydantic import BaseModel, Field


class SetupStatusResponse(BaseModel):
    message: str
    installed: bool
    missing_items: list[str]


class SetupCompleteRequest(BaseModel):
    tmdb_api_key: str = Field(min_length=1)
    qbittorrent_url: str = Field(min_length=1)
    qbittorrent_username: str = Field(min_length=1)
    qbittorrent_password: str = Field(min_length=1)
    download_dir: str = Field(min_length=1)
    media_library_dir: str = Field(min_length=1)
    matching_threshold: int = Field(ge=0, le=100)
    tmdb_language: str = "zh-CN"
    tmdb_region: str = "CN"


class SetupCompleteResponse(BaseModel):
    message: str

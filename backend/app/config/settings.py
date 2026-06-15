from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """系统启动配置。常规业务设置应在网页中保存。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "番剧自动整理管家"
    app_env: str = "development"
    app_secret_key: str = Field(default="development-only-secret-key-change-me")
    backend_host: str = "0.0.0.0"
    backend_port: int = 8031
    data_dir: Path = Path("/app/data")
    database_url: str = "sqlite:////app/data/app.db"
    cache_dir: Path = Path("/app/data/cache")
    log_dir: Path = Path("/app/data/logs")
    download_dir: Path = Path("/downloads")
    media_library_dir: Path = Path("/media")
    high_risk_source_keywords: list[str] = Field(
        default_factory=lambda: [
            "18+",
            "adult",
            "r18",
            "nsfw",
            "成人",
            "色情",
            "盗版",
            "破解",
            "未授权",
        ]
    )
    source_detail_scan_max_pages: int = Field(default=20, ge=0, le=50)


@lru_cache
def get_settings() -> Settings:
    return Settings()

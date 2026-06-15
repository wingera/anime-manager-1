from sqlalchemy.orm import Session

from app.schemas.settings import SettingsUpdateRequest
from app.schemas.setup import SetupCompleteRequest
from app.services.settings_service import get_or_create_settings, update_settings


def get_missing_setup_items(db: Session) -> list[str]:
    settings = get_or_create_settings(db)
    missing_items: list[str] = []

    if not settings.download_dir.strip():
        missing_items.append("下载目录未设置")
    if not settings.media_library_dir.strip():
        missing_items.append("媒体库目录未设置")
    if not settings.qbittorrent_url or not settings.qbittorrent_url.strip():
        missing_items.append("qBittorrent 地址未设置")
    if not settings.qbittorrent_username or not settings.qbittorrent_username.strip():
        missing_items.append("qBittorrent 用户名未设置")
    if not settings.qbittorrent_password:
        missing_items.append("qBittorrent 密码未设置")
    if not settings.tmdb_api_key:
        missing_items.append("TMDB API 密钥未设置")
    if settings.matching_threshold < 0 or settings.matching_threshold > 100:
        missing_items.append("匹配阈值必须在 0 到 100 之间")

    return missing_items


def is_setup_installed(db: Session) -> bool:
    return get_missing_setup_items(db) == []


def complete_setup(db: Session, payload: SetupCompleteRequest) -> None:
    update_settings(
        db,
        SettingsUpdateRequest(
            tmdb_api_key=payload.tmdb_api_key,
            tmdb_language=payload.tmdb_language,
            tmdb_region=payload.tmdb_region,
            qbittorrent_url=payload.qbittorrent_url,
            qbittorrent_username=payload.qbittorrent_username,
            qbittorrent_password=payload.qbittorrent_password,
            download_dir=payload.download_dir,
            media_library_dir=payload.media_library_dir,
            matching_threshold=payload.matching_threshold,
        ),
    )

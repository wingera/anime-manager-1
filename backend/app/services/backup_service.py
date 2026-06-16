from datetime import datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SourceSite
from app.schemas.backup import (
    BackupExportResponse,
    BackupImportRequest,
    BackupSettings,
    BackupSource,
    SourceType,
)
from app.schemas.settings import SettingsUpdateRequest
from app.schemas.sources import SourceSiteCreate
from app.services.settings_service import get_or_create_settings, update_settings
from app.services.source_service import create_source


def export_backup(db: Session) -> BackupExportResponse:
    settings = get_or_create_settings(db)
    sources = db.scalars(select(SourceSite).order_by(SourceSite.created_at, SourceSite.id)).all()

    return BackupExportResponse(
        message="配置备份导出成功",
        exported_at=datetime.utcnow(),
        settings=BackupSettings(
            tmdb_language=settings.tmdb_language,
            tmdb_region=settings.tmdb_region,
            has_tmdb_api_key=bool(settings.tmdb_api_key),
            qbittorrent_url=settings.qbittorrent_url,
            qbittorrent_username=settings.qbittorrent_username,
            has_qbittorrent_password=bool(settings.qbittorrent_password),
            download_provider=settings.download_provider,
            cloud115_enabled=settings.cloud115_enabled,
            cloud115_service_url=settings.cloud115_service_url,
            has_cloud115_service_token=bool(settings.cloud115_service_token),
            download_dir=settings.download_dir,
            media_library_dir=settings.media_library_dir,
            matching_threshold=settings.matching_threshold,
            metadata_proxy_type=settings.metadata_proxy_type,
            metadata_proxy_host=settings.metadata_proxy_host,
            metadata_proxy_port=settings.metadata_proxy_port,
            metadata_proxy_username=settings.metadata_proxy_username,
            has_metadata_proxy_password=bool(settings.metadata_proxy_password),
        ),
        sources=[
            BackupSource(
                name=source.name,
                url=source.url,
                source_type=cast(SourceType, source.source_type),
                enabled=source.enabled,
                auth_note=source.auth_note,
                fetch_interval_minutes=source.fetch_interval_minutes,
                hash_pattern=source.hash_pattern,
                title_cleanup_rules=source.title_cleanup_rules,
            )
            for source in sources
        ],
    )


def import_backup(db: Session, payload: BackupImportRequest) -> None:
    if payload.settings is not None:
        update_settings(
            db,
            SettingsUpdateRequest(
                tmdb_language=payload.settings.tmdb_language,
                tmdb_region=payload.settings.tmdb_region,
                qbittorrent_url=payload.settings.qbittorrent_url,
                qbittorrent_username=payload.settings.qbittorrent_username,
                download_provider=payload.settings.download_provider,
                cloud115_enabled=payload.settings.cloud115_enabled,
                cloud115_service_url=payload.settings.cloud115_service_url,
                download_dir=payload.settings.download_dir,
                media_library_dir=payload.settings.media_library_dir,
                matching_threshold=payload.settings.matching_threshold,
                metadata_proxy_type=payload.settings.metadata_proxy_type,
                metadata_proxy_host=payload.settings.metadata_proxy_host,
                metadata_proxy_port=payload.settings.metadata_proxy_port,
                metadata_proxy_username=payload.settings.metadata_proxy_username,
            ),
        )

    for source in payload.sources:
        create_source(
            db,
            SourceSiteCreate(
                name=source.name,
                url=source.url,
                source_type=source.source_type,
                enabled=source.enabled,
                auth_note=source.auth_note,
                fetch_interval_minutes=source.fetch_interval_minutes,
                hash_pattern=source.hash_pattern,
                title_cleanup_rules=source.title_cleanup_rules,
            ),
        )

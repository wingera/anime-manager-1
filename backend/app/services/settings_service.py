from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppSettings
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest
from app.utils.secrets import decrypt_secret, encrypt_secret, is_encrypted_secret


def get_or_create_settings(db: Session) -> AppSettings:
    settings = db.scalar(select(AppSettings).order_by(AppSettings.id).limit(1))
    if settings is not None:
        return settings

    settings = AppSettings()
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def update_settings(db: Session, payload: SettingsUpdateRequest) -> AppSettings:
    settings = get_or_create_settings(db)
    data = payload.model_dump(exclude_unset=True)

    for field, value in data.items():
        if field in {"tmdb_api_key", "qbittorrent_password"}:
            setattr(settings, field, encrypt_secret(None if value == "" else value))
            continue
        setattr(settings, field, value)

    for field in ("tmdb_api_key", "qbittorrent_password"):
        current_value = getattr(settings, field)
        if current_value and not is_encrypted_secret(current_value):
            setattr(settings, field, encrypt_secret(decrypt_secret(current_value)))

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def to_response(settings: AppSettings) -> SettingsResponse:
    return SettingsResponse(
        id=settings.id,
        tmdb_language=settings.tmdb_language,
        tmdb_region=settings.tmdb_region,
        has_tmdb_api_key=bool(settings.tmdb_api_key),
        qbittorrent_url=settings.qbittorrent_url,
        qbittorrent_username=settings.qbittorrent_username,
        has_qbittorrent_password=bool(settings.qbittorrent_password),
        download_dir=settings.download_dir,
        media_library_dir=settings.media_library_dir,
        matching_threshold=settings.matching_threshold,
        tmdb_include_adult=settings.tmdb_include_adult,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )

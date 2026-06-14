from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.integrations.qbittorrent import test_qbittorrent_connection
from app.integrations.tmdb import test_tmdb_connection
from app.schemas.settings import ConnectionTestResponse, SettingsResponse, SettingsUpdateRequest
from app.services.settings_service import get_or_create_settings, to_response, update_settings
from app.utils.secrets import decrypt_secret

router = APIRouter(prefix="/api/settings", tags=["系统设置"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=SettingsResponse)
def read_settings(db: DbSession) -> SettingsResponse:
    settings = get_or_create_settings(db)
    return to_response(settings)


@router.put("", response_model=SettingsResponse)
def save_settings(
    payload: SettingsUpdateRequest,
    db: DbSession,
) -> SettingsResponse:
    settings = update_settings(db, payload)
    return to_response(settings)


@router.post("/test-tmdb", response_model=ConnectionTestResponse)
def test_tmdb(db: DbSession) -> ConnectionTestResponse:
    settings = get_or_create_settings(db)
    return test_tmdb_connection(
        decrypt_secret(settings.tmdb_api_key),
        settings.tmdb_language,
    )


@router.post("/test-qbittorrent", response_model=ConnectionTestResponse)
def test_qbittorrent(db: DbSession) -> ConnectionTestResponse:
    settings = get_or_create_settings(db)
    return test_qbittorrent_connection(
        settings.qbittorrent_url,
        settings.qbittorrent_username,
        decrypt_secret(settings.qbittorrent_password),
    )

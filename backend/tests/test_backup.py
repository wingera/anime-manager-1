from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppSettings, SourceSite


def test_backup_export_hides_sensitive_plaintext(
    client: TestClient,
    db_session: Session,
) -> None:
    client.put(
        "/api/settings",
        json={
            "tmdb_api_key": "tmdb-secret",
            "qbittorrent_url": "http://127.0.0.1:8080",
            "qbittorrent_username": "admin",
            "qbittorrent_password": "qb-password",
            "download_dir": "/downloads",
            "media_library_dir": "/media",
            "matching_threshold": 86,
        },
    )
    db_session.add(
        SourceSite(
            name="用户授权来源",
            url="https://example.test/rss",
            source_type="rss",
            enabled=False,
            auth_note="用户已确认授权",
            fetch_interval_minutes=30,
            hash_pattern="",
            title_cleanup_rules="",
        )
    )
    db_session.commit()

    response = client.get("/api/backup/export")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "配置备份导出成功"
    assert data["settings"]["has_tmdb_api_key"] is True
    assert data["settings"]["has_qbittorrent_password"] is True
    assert "tmdb-secret" not in response.text
    assert "qb-password" not in response.text
    assert "tmdb_api_key" not in data["settings"]
    assert "qbittorrent_password" not in data["settings"]


def test_backup_import_saves_only_non_sensitive_config(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        "/api/backup/import",
        json={
            "settings": {
                "tmdb_language": "ja-JP",
                "tmdb_region": "JP",
                "qbittorrent_url": "http://127.0.0.1:8080",
                "qbittorrent_username": "admin",
                "download_dir": "/data/downloads",
                "media_library_dir": "/data/media",
                "matching_threshold": 90,
                "tmdb_api_key": "must-not-import",
                "qbittorrent_password": "must-not-import",
            },
            "sources": [
                {
                    "name": "导入来源",
                    "url": "https://example.test/list",
                    "source_type": "webpage",
                    "enabled": False,
                    "auth_note": "",
                    "fetch_interval_minutes": 45,
                    "hash_pattern": "",
                    "title_cleanup_rules": "",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "配置备份导入成功"

    settings = db_session.scalar(select(AppSettings).limit(1))
    assert settings is not None
    assert settings.tmdb_language == "ja-JP"
    assert settings.matching_threshold == 90
    assert settings.tmdb_api_key is None
    assert settings.qbittorrent_password is None
    assert db_session.scalar(select(SourceSite).where(SourceSite.name == "导入来源")) is not None

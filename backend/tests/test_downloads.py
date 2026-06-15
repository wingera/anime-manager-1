from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session() -> Generator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_source_item(client: TestClient, info_hash: str | None = None) -> int:
    source_response = client.post(
        "/api/sources",
        json={
            "name": "用户授权来源",
            "url": "https://example.test/list",
            "source_type": "webpage",
            "enabled": False,
            "auth_note": "",
        },
    )
    source_id = int(source_response.json()["source"]["id"])
    item_response = client.post(
        f"/api/sources/{source_id}/items",
        json={
            "permission_confirmed": True,
            "items": [
                {
                    "title": "测试番剧 S01E01 2026",
                    "url": "https://example.test/item",
                    "info_hash": info_hash or "abcdef1234567890abcdef1234567890abcdef12",
                }
            ]
        },
    )
    assert item_response.status_code == 201
    return int(item_response.json()["items"][0]["id"])


def _confirm_match(client: TestClient, item_id: int) -> None:
    response = client.put(
        f"/api/source-items/{item_id}/match",
        json={
            "tmdb_id": 123,
            "title": "测试番剧",
            "original_title": "Original Test",
            "year": 2026,
            "season_number": 1,
            "episode_number": 1,
            "episode_title": "第一集",
            "match_score": 90,
            "status": "confirmed",
        },
    )
    assert response.status_code == 200


def _configure_qbittorrent(client: TestClient) -> None:
    response = client.put(
        "/api/settings",
        json={
            "qbittorrent_url": "http://127.0.0.1:8080",
            "qbittorrent_username": "admin",
            "qbittorrent_password": "secret-password",
            "download_dir": "/downloads",
        },
    )
    assert response.status_code == 200


def test_list_downloads_defaults_to_empty(client: TestClient) -> None:
    response = client.get("/api/downloads")

    assert response.status_code == 200
    assert response.json() == {"message": "下载任务列表获取成功", "downloads": []}


def test_unconfirmed_match_cannot_create_download(client: TestClient) -> None:
    item_id = _create_source_item(client)

    response = client.post(f"/api/source-items/{item_id}/download")

    assert response.status_code == 400
    assert response.json()["detail"] == "请先确认资料匹配后再创建下载任务"


def test_confirmed_match_can_create_download(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item_id = _create_source_item(client)
    _confirm_match(client, item_id)
    _configure_qbittorrent(client)

    def fake_add_paused_magnet(**kwargs: Any) -> str:
        assert kwargs["magnet_uri"].startswith("magnet:?xt=urn:btih:")
        assert kwargs["save_path"] == "/downloads"
        return "abcdef1234567890abcdef1234567890abcdef12"

    monkeypatch.setattr("app.services.download_service.add_paused_magnet", fake_add_paused_magnet)

    response = client.post(f"/api/source-items/{item_id}/download")

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "下载任务已创建"
    assert data["download"]["source_item_id"] == item_id
    assert data["download"]["status"] == "submitted"
    assert data["download"]["progress"] == 0
    assert data["download"]["qbittorrent_hash"] == "abcdef1234567890abcdef1234567890abcdef12"


def test_same_source_item_cannot_create_duplicate_download(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item_id = _create_source_item(client)
    _confirm_match(client, item_id)
    _configure_qbittorrent(client)
    monkeypatch.setattr(
        "app.services.download_service.add_paused_magnet",
        lambda **_kwargs: "abcdef1234567890abcdef1234567890abcdef12",
    )

    first_response = client.post(f"/api/source-items/{item_id}/download")
    second_response = client.post(f"/api/source-items/{item_id}/download")

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "下载任务已存在"


def test_unconfigured_qbittorrent_returns_chinese_message(client: TestClient) -> None:
    item_id = _create_source_item(client)
    _confirm_match(client, item_id)

    response = client.post(f"/api/source-items/{item_id}/download")

    assert response.status_code == 400
    assert response.json()["detail"] == "请先填写 qBittorrent 地址、用户名和密码"


def test_delete_download_record_success(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item_id = _create_source_item(client)
    _confirm_match(client, item_id)
    _configure_qbittorrent(client)
    monkeypatch.setattr(
        "app.services.download_service.add_paused_magnet",
        lambda **_kwargs: "abcdef1234567890abcdef1234567890abcdef12",
    )
    create_response = client.post(f"/api/source-items/{item_id}/download")
    download_id = int(create_response.json()["download"]["id"])

    response = client.delete(f"/api/downloads/{download_id}")

    assert response.status_code == 200
    assert response.json() == {"message": "下载任务记录已删除"}
    assert client.get("/api/downloads").json()["downloads"] == []


def test_refresh_missing_download_returns_chinese_404(client: TestClient) -> None:
    response = client.post("/api/downloads/999/refresh")

    assert response.status_code == 404
    assert response.json()["detail"] == "下载任务不存在"

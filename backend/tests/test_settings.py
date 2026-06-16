from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session]:
        session = testing_session_local()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_get_settings_returns_default_config(client: TestClient) -> None:
    response = client.get("/api/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["tmdb_language"] == "zh-CN"
    assert data["tmdb_region"] == "CN"
    assert data["download_dir"] == "/downloads"
    assert data["media_library_dir"] == "/media"
    assert data["matching_threshold"] == 85
    assert data["tmdb_include_adult"] is False
    assert data["has_tmdb_api_key"] is False
    assert data["has_qbittorrent_password"] is False
    assert data["metadata_proxy_type"] == "none"
    assert data["metadata_proxy_host"] is None
    assert data["metadata_proxy_port"] is None
    assert data["metadata_proxy_username"] is None
    assert data["has_metadata_proxy_password"] is False
    assert "tmdb_api_key" not in data
    assert "qbittorrent_password" not in data
    assert "metadata_proxy_password" not in data


def test_put_settings_saves_normal_fields(client: TestClient) -> None:
    response = client.put(
        "/api/settings",
        json={
            "tmdb_language": "ja-JP",
            "tmdb_region": "JP",
            "download_dir": "/data/downloads",
            "media_library_dir": "/data/media",
            "matching_threshold": 90,
            "tmdb_include_adult": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tmdb_language"] == "ja-JP"
    assert data["tmdb_region"] == "JP"
    assert data["download_dir"] == "/data/downloads"
    assert data["media_library_dir"] == "/data/media"
    assert data["matching_threshold"] == 90
    assert data["tmdb_include_adult"] is True


def test_put_settings_saves_metadata_proxy_without_plaintext_password(
    client: TestClient,
) -> None:
    response = client.put(
        "/api/settings",
        json={
            "metadata_proxy_type": "socks5",
            "metadata_proxy_host": "127.0.0.1",
            "metadata_proxy_port": 1080,
            "metadata_proxy_username": "proxy-user",
            "metadata_proxy_password": "proxy-secret",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["metadata_proxy_type"] == "socks5"
    assert data["metadata_proxy_host"] == "127.0.0.1"
    assert data["metadata_proxy_port"] == 1080
    assert data["metadata_proxy_username"] == "proxy-user"
    assert data["has_metadata_proxy_password"] is True
    assert "proxy-secret" not in response.text
    assert "metadata_proxy_password" not in data


def test_put_settings_does_not_return_sensitive_plaintext(client: TestClient) -> None:
    response = client.put(
        "/api/settings",
        json={
            "tmdb_api_key": "secret-tmdb-key",
            "qbittorrent_url": "http://127.0.0.1:8080",
            "qbittorrent_username": "admin",
            "qbittorrent_password": "secret-password",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["has_tmdb_api_key"] is True
    assert data["has_qbittorrent_password"] is True
    assert "secret-tmdb-key" not in response.text
    assert "secret-password" not in response.text
    assert "tmdb_api_key" not in data
    assert "qbittorrent_password" not in data


def test_unconfigured_tmdb_test_returns_chinese_message(client: TestClient) -> None:
    response = client.post("/api/settings/test-tmdb")

    assert response.status_code == 200
    assert response.json() == {"success": False, "message": "请先填写 TMDB API 密钥"}


def test_unconfigured_qbittorrent_test_returns_chinese_message(client: TestClient) -> None:
    response = client.post("/api/settings/test-qbittorrent")

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "message": "请先填写 qBittorrent 地址、用户名和密码",
    }


def test_qbittorrent_test_accepts_204_login_success(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client.put(
        "/api/settings",
        json={
            "qbittorrent_url": "http://127.0.0.1:8080",
            "qbittorrent_username": "admin",
            "qbittorrent_password": "secret-password",
        },
    )

    class FakeResponse:
        status_code = 204
        text = ""
        cookies = {"QBT_SID_8080": "session-id"}

    def fake_post(*args: object, **kwargs: object) -> FakeResponse:
        return FakeResponse()

    monkeypatch.setattr("app.integrations.qbittorrent.httpx.post", fake_post)

    response = client.post("/api/settings/test-qbittorrent")

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "qBittorrent 连接成功"}

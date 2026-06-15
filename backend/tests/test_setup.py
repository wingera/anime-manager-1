from fastapi.testclient import TestClient


def test_setup_status_reports_uninstalled_when_required_items_missing(
    client: TestClient,
) -> None:
    response = client.get("/api/setup/status")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "安装状态获取成功"
    assert data["installed"] is False
    assert "TMDB API 密钥未设置" in data["missing_items"]
    assert "qBittorrent 密码未设置" in data["missing_items"]


def test_setup_status_reports_installed_after_complete_config(client: TestClient) -> None:
    response = client.post(
        "/api/setup/complete",
        json={
            "tmdb_api_key": "tmdb-secret",
            "qbittorrent_url": "http://127.0.0.1:8080",
            "qbittorrent_username": "admin",
            "qbittorrent_password": "qb-password",
            "download_dir": "/tmp/downloads",
            "media_library_dir": "/tmp/media",
            "matching_threshold": 88,
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "安装向导已完成"

    status_response = client.get("/api/setup/status")
    data = status_response.json()
    assert data["message"] == "安装状态获取成功"
    assert data["installed"] is True
    assert data["missing_items"] == []

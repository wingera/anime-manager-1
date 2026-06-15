from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app


def _test_engine() -> Engine:
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _fake_torrent_files() -> list[dict[str, Any]]:
    return [
        {
            "index": 0,
            "name": "Show.Name.S01E01.mkv",
            "size": 1_800_000_000,
            "progress": 0,
            "priority": 1,
        },
        {
            "index": 1,
            "name": "Show.Name.S01E02.mp4",
            "size": 1_600_000_000,
            "progress": 0,
            "priority": 1,
        },
        {
            "index": 2,
            "name": "sample-preview.mp4",
            "size": 20_000_000,
            "progress": 0,
            "priority": 1,
        },
        {
            "index": 3,
            "name": "Show.Name.S01E01.ass",
            "size": 80_000,
            "progress": 0,
            "priority": 1,
        },
        {
            "index": 4,
            "name": "readme.txt",
            "size": 2_000,
            "progress": 0,
            "priority": 1,
        },
    ]


def _create_source_item(client: TestClient) -> int:
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
                    "info_hash": "abcdef1234567890abcdef1234567890abcdef12",
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
            "media_library_dir": "/media",
        },
    )
    assert response.status_code == 200


def _create_download(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    *,
    torrent_hash: str | None = "abcdef1234567890abcdef1234567890abcdef12",
) -> int:
    item_id = _create_source_item(client)
    _confirm_match(client, item_id)
    _configure_qbittorrent(client)
    monkeypatch.setattr(
        "app.services.download_service.add_paused_magnet",
        lambda **_kwargs: torrent_hash or "",
    )
    response = client.post(f"/api/source-items/{item_id}/download")
    assert response.status_code == 201
    return int(response.json()["download"]["id"])


def _analyze_files(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> list[dict[str, Any]]:
    download_id = _create_download(client, monkeypatch)
    monkeypatch.setattr(
        "app.services.file_analysis_service.get_torrent_files",
        lambda **_kwargs: _fake_torrent_files(),
    )
    response = client.post(f"/api/downloads/{download_id}/files/analyze")
    assert response.status_code == 200
    assert response.json()["message"] == "文件分析完成"
    return cast(list[dict[str, Any]], response.json()["files"])


@pytest.fixture()
def db_session() -> Generator[Session]:
    engine = _test_engine()
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


def test_analyze_requires_qbittorrent_hash(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    download_id = _create_download(client, monkeypatch, torrent_hash=None)

    response = client.post(f"/api/downloads/{download_id}/files/analyze")

    assert response.status_code == 400
    assert response.json()["detail"] == "下载器尚未返回任务哈希，请稍后刷新。"


def test_analyze_writes_download_files(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _analyze_files(client, monkeypatch)

    assert len(files) == 5
    assert files[0]["name"] == "Show.Name.S01E01.mkv"
    assert files[0]["file_type"] == "video"
    assert files[0]["episode_number"] == 1


def test_largest_video_is_selected_by_default(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _analyze_files(client, monkeypatch)
    largest = next(file for file in files if file["name"] == "Show.Name.S01E01.mkv")

    assert largest["selected"] is True


def test_sample_file_is_not_selected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _analyze_files(client, monkeypatch)
    sample = next(file for file in files if file["name"] == "sample-preview.mp4")

    assert sample["file_type"] == "sample"
    assert sample["selected"] is False


def test_non_video_non_subtitle_is_not_selected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _analyze_files(client, monkeypatch)
    document = next(file for file in files if file["name"] == "readme.txt")

    assert document["file_type"] == "document"
    assert document["selected"] is False


def test_update_download_file_allows_manual_override(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = _analyze_files(client, monkeypatch)
    sample = next(file for file in files if file["name"] == "sample-preview.mp4")

    response = client.put(
        f"/api/download-files/{sample['id']}",
        json={"selected": True, "season_number": 1, "episode_number": 3},
    )

    assert response.status_code == 200
    assert response.json()["file"]["selected"] is True
    assert response.json()["file"]["season_number"] == 1
    assert response.json()["file"]["episode_number"] == 3


def test_apply_priority_sets_unselected_files_to_zero(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    download_id = _create_download(client, monkeypatch)
    monkeypatch.setattr(
        "app.services.file_analysis_service.get_torrent_files",
        lambda **_kwargs: _fake_torrent_files(),
    )
    client.post(f"/api/downloads/{download_id}/files/analyze")
    calls: list[dict[str, Any]] = []

    def fake_set_file_priority(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(
        "app.services.file_analysis_service.set_file_priority",
        fake_set_file_priority,
    )

    response = client.post(f"/api/downloads/{download_id}/files/apply-priority")

    assert response.status_code == 200
    assert response.json()["message"] == "文件优先级已应用"
    assert any(call["priority"] == 0 and 2 in call["file_indexes"] for call in calls)
    assert any(call["priority"] == 0 and 4 in call["file_indexes"] for call in calls)


def test_rename_preview_requires_confirmed_match(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item_id = _create_source_item(client)
    _configure_qbittorrent(client)
    monkeypatch.setattr(
        "app.services.download_service.add_paused_magnet",
        lambda **_kwargs: "abcdef1234567890abcdef1234567890abcdef12",
    )
    match_payload = {
        "tmdb_id": 123,
        "title": "测试番剧",
        "original_title": "Original Test",
        "year": 2026,
        "season_number": 1,
        "episode_number": 1,
        "episode_title": "第一集",
        "match_score": 90,
        "status": "confirmed",
    }
    client.put(f"/api/source-items/{item_id}/match", json={**match_payload, "status": "pending"})
    client.put(f"/api/source-items/{item_id}/match", json=match_payload)
    download_response = client.post(f"/api/source-items/{item_id}/download")
    download_id = int(download_response.json()["download"]["id"])
    client.put(f"/api/source-items/{item_id}/match", json={**match_payload, "status": "pending"})

    response = client.post(f"/api/downloads/{download_id}/rename-preview")

    assert response.status_code == 400
    assert response.json()["detail"] == "请先确认资料匹配。"


def test_confirmed_match_generates_emby_rename_preview(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    download_id = _create_download(client, monkeypatch)
    monkeypatch.setattr(
        "app.services.file_analysis_service.get_torrent_files",
        lambda **_kwargs: _fake_torrent_files(),
    )
    client.post(f"/api/downloads/{download_id}/files/analyze")

    response = client.post(f"/api/downloads/{download_id}/rename-preview")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "命名预览已生成"
    assert data["previews"][0]["original_path"] == "Show.Name.S01E01.mkv"
    assert data["previews"][0]["target_path"] == (
        "/media/测试番剧 (2026) [tmdbid=123]/Season 01/测试番剧 - S01E01 - 第一集.mkv"
    )


def test_rename_preview_does_not_touch_filesystem(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    download_id = _create_download(client, monkeypatch)
    media_dir = tmp_path / "media"
    client.put("/api/settings", json={"media_library_dir": str(media_dir)})
    monkeypatch.setattr(
        "app.services.file_analysis_service.get_torrent_files",
        lambda **_kwargs: _fake_torrent_files(),
    )
    client.post(f"/api/downloads/{download_id}/files/analyze")

    response = client.post(f"/api/downloads/{download_id}/rename-preview")

    assert response.status_code == 200
    assert not Path(response.json()["previews"][0]["target_path"]).exists()
    assert not media_dir.exists()

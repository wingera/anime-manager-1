from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models import DownloadFile, DownloadTask, MediaMatch, OperationLog, SourceItem
from app.integrations.nas115 import rename_file
from app.main import app


def _create_source_item(db: Session) -> SourceItem:
    item = SourceItem(
        source_id=1,
        title="NAS 测试番剧 S01",
        url="https://example.test/item",
        info_hash="abcdef1234567890abcdef1234567890abcdef12",
        magnet_uri="magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12",
        status="matched",
    )
    db.add(item)
    db.flush()
    db.add(
        MediaMatch(
            source_item_id=item.id,
            tmdb_id=123,
            title="NAS 测试番剧",
            year=2026,
            season_number=1,
            episode_number=1,
            match_score=90,
            status="confirmed",
        )
    )
    db.commit()
    db.refresh(item)
    return item


def _fake_files() -> list[dict[str, object]]:
    return [
        {
            "id": "file-1",
            "name": "NAS.测试番剧.S01E02.mkv",
            "parent_id": "parent-1",
            "size": 1_500_000_000,
            "progress": 1,
        }
    ]


def _fake_status() -> dict[str, object]:
    return {"status": "completed", "progress": 1.0, "error_message": None}


def _configure_nas115(client: TestClient, *, token: str = "nas-secret-token") -> None:
    response = client.put(
        "/api/settings",
        json={
            "download_provider": "nas115",
            "cloud115_enabled": True,
            "cloud115_service_url": "http://192.168.1.19:9527",
            "cloud115_service_token": token,
        },
    )
    assert response.status_code == 200


def _create_nas_download(
    client: TestClient,
    db: Session,
    monkeypatch: Any,
) -> int:
    item = _create_source_item(db)

    def fake_add_magnet_task(**kwargs: object) -> str:
        assert kwargs["service_url"] == "http://192.168.1.19:9527"
        assert kwargs["token"] == "nas-secret-token"
        assert str(kwargs["magnet_uri"]).startswith("magnet:?xt=urn:btih:")
        return "task-123"

    monkeypatch.setattr(
        "app.services.download_service.add_nas115_magnet_task",
        fake_add_magnet_task,
    )
    response = client.post(f"/api/source-items/{item.id}/download")
    assert response.status_code == 201
    return int(response.json()["download"]["id"])


def test_unconfigured_nas115_connection_returns_chinese_message(client: TestClient) -> None:
    client.put("/api/settings", json={"download_provider": "nas115", "cloud115_service_url": ""})

    response = client.post("/api/settings/test-nas115")

    assert response.status_code == 200
    assert response.json() == {"success": False, "message": "请先填写 NAS 115 服务地址"}


def test_settings_encrypts_nas115_token_and_never_returns_plaintext(
    client: TestClient,
    db_session: Session,
) -> None:
    _configure_nas115(client)

    response = client.get("/api/settings")
    settings_row = db_session.execute(select(OperationLog)).all()

    assert response.status_code == 200
    assert response.json()["has_cloud115_service_token"] is True
    assert "nas-secret-token" not in response.text
    assert "cloud115_service_token" not in response.json()
    assert "nas-secret-token" not in str(settings_row)


def test_nas115_can_create_download_task(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    _configure_nas115(client)
    item = _create_source_item(db_session)
    monkeypatch.setattr(
        "app.services.download_service.add_nas115_magnet_task",
        lambda **_kwargs: "task-123",
    )

    response = client.post(f"/api/source-items/{item.id}/download")

    assert response.status_code == 201
    download = response.json()["download"]
    assert download["provider"] == "nas115"
    assert download["provider_task_id"] == "task-123"
    assert download["status"] == "submitted"


def test_nas115_refresh_uses_remote_task_status(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    _configure_nas115(client)
    download_id = _create_nas_download(client, db_session, monkeypatch)
    monkeypatch.setattr(
        "app.services.download_service.get_nas115_task_status",
        lambda **_kwargs: _fake_status(),
    )

    response = client.post(f"/api/downloads/{download_id}/refresh")

    assert response.status_code == 200
    assert response.json()["download"]["status"] == "completed"
    assert response.json()["download"]["progress"] == 1.0


def test_nas115_file_list_writes_download_files(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    _configure_nas115(client)
    download_id = _create_nas_download(client, db_session, monkeypatch)
    monkeypatch.setattr(
        "app.services.file_analysis_service.list_nas115_task_files",
        lambda **_kwargs: _fake_files(),
    )

    response = client.post(f"/api/downloads/{download_id}/files/analyze")

    assert response.status_code == 200
    file_data = response.json()["files"][0]
    assert file_data["provider_file_id"] == "file-1"
    assert file_data["parent_id"] == "parent-1"
    assert file_data["name"] == "NAS.测试番剧.S01E02.mkv"
    assert file_data["file_type"] == "video"


def test_nas115_apply_priority_saves_selection_without_remote_call(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    _configure_nas115(client)
    download_id = _create_nas_download(client, db_session, monkeypatch)

    response = client.post(f"/api/downloads/{download_id}/files/apply-priority")

    assert response.status_code == 200
    assert response.json()["message"] == "115 网盘模式不需要设置下载器文件优先级，已保存文件选择。"


def test_nas115_rename_file_reports_missing_service_capability() -> None:
    with pytest.raises(ValueError, match="115 服务未提供该能力，请检查 NAS 服务接口。"):
        rename_file("http://192.168.1.19:9527", "nas-secret-token", "file-1", "新文件名.mkv")


def test_nas115_rename_calls_remote_file_rename(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    _configure_nas115(client)
    download_id = _create_nas_download(client, db_session, monkeypatch)
    download = db_session.get(DownloadTask, download_id)
    assert download is not None
    db_session.add(
        DownloadFile(
            download_task_id=download_id,
            file_index=0,
            provider_file_id="file-1",
            parent_id="parent-1",
            name="NAS.测试番剧.S01E02.mkv",
            size=1_500_000_000,
            progress=1,
            file_type="video",
            selected=True,
            episode_number=2,
        )
    )
    db_session.commit()
    client.post(f"/api/tasks/{download_id}/rename-preview")
    calls: list[dict[str, str]] = []
    monkeypatch.setattr(
        "app.services.rename_service.check_nas115_name_exists",
        lambda **_kwargs: False,
    )
    monkeypatch.setattr(
        "app.services.rename_service.rename_nas115_file",
        lambda **kwargs: calls.append(kwargs),
    )

    response = client.post(f"/api/tasks/{download_id}/rename-apply")

    assert response.status_code == 200
    assert calls[0]["file_id"] == "file-1"
    assert calls[0]["new_name"] == "NAS 测试番剧 S01 - 02.mkv"


def test_nas115_rename_conflict_does_not_call_remote(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    _configure_nas115(client)
    download_id = _create_nas_download(client, db_session, monkeypatch)
    db_session.add_all(
        [
            DownloadFile(
                download_task_id=download_id,
                file_index=0,
                provider_file_id="file-1",
                parent_id="parent-1",
                name="a.S01E02.mkv",
                size=1_000_000_000,
                progress=1,
                file_type="video",
                selected=True,
                episode_number=2,
            ),
            DownloadFile(
                download_task_id=download_id,
                file_index=1,
                provider_file_id="file-2",
                parent_id="parent-1",
                name="b.S01E02.mkv",
                size=1_000_000_000,
                progress=1,
                file_type="video",
                selected=True,
                episode_number=2,
            ),
        ]
    )
    db_session.commit()
    client.post(f"/api/tasks/{download_id}/rename-preview")
    calls: list[dict[str, str]] = []
    monkeypatch.setattr(
        "app.services.rename_service.rename_nas115_file",
        lambda **kwargs: calls.append(kwargs),
    )

    response = client.post(f"/api/tasks/{download_id}/rename-apply")

    assert response.status_code == 200
    assert response.json()["actions"] == []
    assert calls == []


def test_nas115_rollback_calls_remote_with_old_name(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    _configure_nas115(client)
    download_id = _create_nas_download(client, db_session, monkeypatch)
    db_session.add(
        DownloadFile(
            download_task_id=download_id,
            file_index=0,
            provider_file_id="file-1",
            parent_id="parent-1",
            name="NAS.测试番剧.S01E02.mkv",
            size=1_500_000_000,
            progress=1,
            file_type="video",
            selected=True,
            episode_number=2,
        )
    )
    db_session.commit()
    client.post(f"/api/tasks/{download_id}/rename-preview")
    monkeypatch.setattr("app.services.rename_service.check_nas115_name_exists", lambda **_k: False)
    monkeypatch.setattr("app.services.rename_service.rename_nas115_file", lambda **_k: None)
    action_response = client.post(f"/api/tasks/{download_id}/rename-apply")
    action_id = action_response.json()["actions"][0]["id"]
    calls: list[dict[str, str]] = []
    monkeypatch.setattr(
        "app.services.rename_service.rename_nas115_file",
        lambda **kwargs: calls.append(kwargs),
    )

    response = client.post(f"/api/rename-actions/{action_id}/rollback")

    assert response.status_code == 200
    assert calls[0]["file_id"] == "file-1"
    assert calls[0]["new_name"] == "NAS.测试番剧.S01E02.mkv"


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

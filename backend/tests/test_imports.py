import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models import (
    AppSettings,
    DownloadFile,
    DownloadTask,
    MediaMatch,
    RenamePreview,
    SourceItem,
    SourceSite,
)
from app.main import app


def _test_engine() -> Engine:
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


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


def _configure_paths(db: Session, download_dir: Path, media_dir: Path) -> None:
    settings = db.get(AppSettings, 1)
    if settings is None:
        settings = AppSettings(id=1)
    settings.download_dir = str(download_dir)
    settings.media_library_dir = str(media_dir)
    db.add(settings)
    db.commit()


def _create_download(db: Session, save_path: Path) -> DownloadTask:
    source = SourceSite(
        name="用户授权来源",
        url="https://example.test/list",
        source_type="webpage",
        enabled=False,
    )
    db.add(source)
    db.flush()
    item = SourceItem(
        source_id=source.id,
        title="测试番剧 S01E01 2026",
        url="https://example.test/item",
        info_hash="abcdef1234567890abcdef1234567890abcdef12",
        magnet_uri="magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12",
        status="pending",
    )
    db.add(item)
    db.flush()
    db.add(
        MediaMatch(
            source_item_id=item.id,
            tmdb_id=123,
            title="测试番剧",
            original_title="Original Test",
            year=2026,
            season_number=1,
            episode_number=1,
            episode_title="第一集",
            match_score=90,
            status="confirmed",
        )
    )
    download = DownloadTask(
        source_item_id=item.id,
        magnet_uri=item.magnet_uri,
        qbittorrent_hash=item.info_hash,
        save_path=str(save_path),
        status="pending_import",
    )
    db.add(download)
    db.commit()
    db.refresh(download)
    return download


def _add_file(
    db: Session,
    download: DownloadTask,
    *,
    file_index: int = 0,
    name: str = "Show.Name.S01E01.mkv",
    file_type: str = "video",
    selected: bool = True,
    season_number: int | None = 1,
    episode_number: int | None = 1,
) -> DownloadFile:
    download_file = DownloadFile(
        download_task_id=download.id,
        file_index=file_index,
        name=name,
        size=1_000_000_000,
        progress=1,
        priority=1,
        file_type=file_type,
        selected=selected,
        analysis_score=100,
        season_number=season_number,
        episode_number=episode_number,
    )
    db.add(download_file)
    db.commit()
    db.refresh(download_file)
    return download_file


def _add_preview(
    db: Session,
    download_file: DownloadFile,
    target_path: Path,
    *,
    conflict: bool = False,
) -> RenamePreview:
    preview = RenamePreview(
        download_file_id=download_file.id,
        original_path=download_file.name,
        target_path=str(target_path),
        conflict=conflict,
    )
    db.add(preview)
    db.commit()
    db.refresh(preview)
    return preview


def _write_source_file(base_dir: Path, relative_path: str, content: str = "video") -> Path:
    source_path = base_dir / relative_path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(content, encoding="utf-8")
    return source_path


def _target_path(media_dir: Path) -> Path:
    return (
        media_dir
        / "测试番剧 (2026) [tmdbid=123]"
        / "Season 01"
        / "测试番剧 - S01E01 - 第一集.mkv"
    )


def test_import_requires_rename_preview(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    download_dir = tmp_path / "downloads"
    media_dir = tmp_path / "media"
    _configure_paths(db_session, download_dir, media_dir)
    download = _create_download(db_session, download_dir)
    _add_file(db_session, download)

    response = client.post(f"/api/downloads/{download.id}/import")

    assert response.status_code == 400
    assert response.json()["detail"] == "请先生成命名预览。"


def test_import_records_failed_action_when_source_file_missing(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    download_dir = tmp_path / "downloads"
    media_dir = tmp_path / "media"
    _configure_paths(db_session, download_dir, media_dir)
    download = _create_download(db_session, download_dir)
    download_file = _add_file(db_session, download)
    _add_preview(
        db_session,
        download_file,
        media_dir / "测试番剧 (2026) [tmdbid=123]/Season 01/测试番剧 - S01E01 - 第一集.mkv",
    )

    response = client.post(f"/api/downloads/{download.id}/import")

    assert response.status_code == 200
    assert response.json()["message"] == "入库执行完成"
    import_id = response.json()["import_job"]["id"]
    detail = client.get(f"/api/imports/{import_id}").json()
    assert detail["import_job"]["status"] == "failed"
    assert detail["actions"][0]["status"] == "failed"
    assert detail["actions"][0]["error_message"] == "源文件不存在"


def test_import_can_hardlink_source_file(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    download_dir = tmp_path / "downloads"
    media_dir = tmp_path / "media"
    _configure_paths(db_session, download_dir, media_dir)
    download = _create_download(db_session, download_dir)
    download_file = _add_file(db_session, download)
    source_path = _write_source_file(download_dir, download_file.name)
    target_path = _target_path(media_dir)
    _add_preview(db_session, download_file, target_path)

    response = client.post(f"/api/downloads/{download.id}/import")

    assert response.status_code == 200
    assert target_path.exists()
    assert os.stat(source_path).st_ino == os.stat(target_path).st_ino
    import_id = response.json()["import_job"]["id"]
    detail = client.get(f"/api/imports/{import_id}").json()
    assert detail["import_job"]["status"] == "completed"
    assert detail["actions"][0]["action_type"] == "hardlink"
    assert detail["actions"][0]["status"] == "completed"


def test_import_does_not_overwrite_existing_target_file(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    download_dir = tmp_path / "downloads"
    media_dir = tmp_path / "media"
    _configure_paths(db_session, download_dir, media_dir)
    download = _create_download(db_session, download_dir)
    download_file = _add_file(db_session, download)
    _write_source_file(download_dir, download_file.name, "new")
    target_path = _target_path(media_dir)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("old", encoding="utf-8")
    _add_preview(db_session, download_file, target_path)

    response = client.post(f"/api/downloads/{download.id}/import")

    assert response.status_code == 200
    assert target_path.read_text(encoding="utf-8") == "old"
    import_id = response.json()["import_job"]["id"]
    detail = client.get(f"/api/imports/{import_id}").json()
    assert detail["actions"][0]["status"] == "failed"
    assert detail["actions"][0]["error_message"] == "目标文件已存在"


def test_import_target_path_must_stay_inside_media_library(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    download_dir = tmp_path / "downloads"
    media_dir = tmp_path / "media"
    _configure_paths(db_session, download_dir, media_dir)
    download = _create_download(db_session, download_dir)
    download_file = _add_file(db_session, download)
    _write_source_file(download_dir, download_file.name)
    outside_target = tmp_path / "outside/测试番剧.mkv"
    _add_preview(db_session, download_file, outside_target)

    response = client.post(f"/api/downloads/{download.id}/import")

    assert response.status_code == 200
    import_id = response.json()["import_job"]["id"]
    detail = client.get(f"/api/imports/{import_id}").json()
    assert detail["actions"][0]["status"] == "failed"
    assert detail["actions"][0]["error_message"] == "文件路径不安全，已拒绝操作。"
    assert not outside_target.exists()


def test_rollback_removes_hardlink_or_copy_target_only(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    download_dir = tmp_path / "downloads"
    media_dir = tmp_path / "media"
    _configure_paths(db_session, download_dir, media_dir)
    download = _create_download(db_session, download_dir)
    download_file = _add_file(db_session, download)
    source_path = _write_source_file(download_dir, download_file.name)
    target_path = _target_path(media_dir)
    _add_preview(db_session, download_file, target_path)

    def fail_hardlink(_source: Path, _target: Path) -> None:
        raise OSError("不支持硬链接")

    monkeypatch.setattr("app.services.import_service.os.link", fail_hardlink)
    import_response = client.post(f"/api/downloads/{download.id}/import")
    import_id = import_response.json()["import_job"]["id"]
    assert target_path.exists()
    assert target_path.read_text(encoding="utf-8") == source_path.read_text(encoding="utf-8")

    response = client.post(f"/api/imports/{import_id}/rollback")

    assert response.status_code == 200
    assert response.json()["message"] == "入库回滚完成"
    assert source_path.exists()
    assert not target_path.exists()
    detail = client.get(f"/api/imports/{import_id}").json()
    assert detail["import_job"]["status"] == "rolled_back"
    assert detail["actions"][0]["action_type"] == "copy"
    assert detail["actions"][0]["status"] == "rolled_back"


def test_rollback_missing_import_returns_chinese_404(client: TestClient) -> None:
    response = client.post("/api/imports/999999/rollback")

    assert response.status_code == 404
    assert response.json()["detail"] == "入库任务不存在"


def test_list_imports_returns_empty_list_by_default(client: TestClient) -> None:
    response = client.get("/api/imports")

    assert response.status_code == 200
    assert response.json() == {"message": "入库记录获取成功", "imports": []}


def test_get_import_detail_returns_file_actions(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    download_dir = tmp_path / "downloads"
    media_dir = tmp_path / "media"
    _configure_paths(db_session, download_dir, media_dir)
    download = _create_download(db_session, download_dir)
    download_file = _add_file(db_session, download)
    _write_source_file(download_dir, download_file.name)
    target_path = _target_path(media_dir)
    _add_preview(db_session, download_file, target_path)
    import_response = client.post(f"/api/downloads/{download.id}/import")
    import_id = import_response.json()["import_job"]["id"]

    response = client.get(f"/api/imports/{import_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "入库详情获取成功"
    assert data["import_job"]["id"] == import_id
    assert data["actions"][0]["source_path"] == str(download_dir / download_file.name)
    assert data["actions"][0]["target_path"] == str(target_path)


def test_subtitle_preview_follows_same_episode_video_target(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    download_dir = tmp_path / "downloads"
    media_dir = tmp_path / "media"
    _configure_paths(db_session, download_dir, media_dir)
    download = _create_download(db_session, download_dir)
    _add_file(db_session, download, file_index=0, name="Show.Name.S01E01.mkv", file_type="video")
    subtitle = _add_file(
        db_session,
        download,
        file_index=1,
        name="Show.Name.S01E01.ass",
        file_type="subtitle",
        selected=True,
    )

    response = client.post(f"/api/downloads/{download.id}/rename-preview")

    assert response.status_code == 200
    previews = response.json()["previews"]
    subtitle_preview = next(item for item in previews if item["download_file_id"] == subtitle.id)
    assert subtitle_preview["target_path"].endswith("测试番剧 - S01E01 - 第一集.ass")
    assert subtitle_preview["conflict"] is False
    assert subtitle_preview["warning_message"] is None

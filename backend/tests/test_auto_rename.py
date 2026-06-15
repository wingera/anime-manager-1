from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import DownloadFile, DownloadTask, MediaMatch, SourceItem
from app.utils.rename_parser import (
    build_target_name,
    classify_rename_file,
    extract_episode_number,
    sanitize_name_part,
)


def _create_download_with_files(db: Session) -> DownloadTask:
    item = SourceItem(
        source_id=1,
        title="测试/番剧: S01",
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
            title="测试番剧",
            year=2026,
            season_number=1,
            episode_number=1,
            match_score=90,
            status="confirmed",
        )
    )
    download = DownloadTask(
        source_item_id=item.id,
        qbittorrent_hash="abcdef1234567890abcdef1234567890abcdef12",
        magnet_uri=item.magnet_uri,
        save_path="/downloads",
        status="downloading",
        progress=0.5,
    )
    db.add(download)
    db.flush()
    db.add_all(
        [
            DownloadFile(
                download_task_id=download.id,
                file_index=0,
                name="测试.番剧.S01E02.mkv",
                size=1_500_000_000,
                progress=1,
                file_type="video",
                selected=True,
                episode_number=2,
            ),
            DownloadFile(
                download_task_id=download.id,
                file_index=1,
                name="测试.番剧.S01E02.ass",
                size=80_000,
                progress=1,
                file_type="subtitle",
                selected=True,
                episode_number=2,
            ),
            DownloadFile(
                download_task_id=download.id,
                file_index=2,
                name="无法识别.mkv",
                size=1_200_000_000,
                progress=1,
                file_type="video",
                selected=True,
                episode_number=None,
            ),
        ]
    )
    db.commit()
    db.refresh(download)
    return download


def test_template_rendering_keeps_extension_and_padding() -> None:
    target = build_target_name(
        title="测试/番剧",
        original_name="Show.Name.S01E02",
        extension=".mkv",
        episode_number=2,
        template="{clean_title} - {episode}{ext}",
        episode_padding=2,
    )

    assert target == "测试番剧 - 02.mkv"


def test_episode_detection_supports_common_patterns() -> None:
    assert extract_episode_number("Show.S01E02.mkv") == 2
    assert extract_episode_number("测试 第02话.mp4") == 2
    assert extract_episode_number("测试 EP02.mkv") == 2
    assert extract_episode_number("测试 [02].ass") == 2


def test_illegal_characters_are_removed() -> None:
    assert sanitize_name_part('/\\:*?"<>|测试') == "测试"


def test_file_type_detection_for_rename() -> None:
    assert classify_rename_file("a.mkv") == "video"
    assert classify_rename_file("a.ass") == "subtitle"
    assert classify_rename_file("a.jpg") == "image"
    assert classify_rename_file("a.pdf") == "document"
    assert classify_rename_file("a.bin") == "other"


def test_rule_defaults_to_disabled(client: TestClient) -> None:
    response = client.get("/api/rename/rule")

    assert response.status_code == 200
    rule = response.json()["rule"]
    assert rule["enabled"] is False
    assert rule["auto_execute"] is False
    assert rule["name_template"] == "{clean_title} - {episode}{ext}"


def test_saving_rule_uses_chinese_message(client: TestClient) -> None:
    response = client.put(
        "/api/rename/rule",
        json={
            "enabled": True,
            "auto_execute": False,
            "name_template": "{clean_title} - {episode}{ext}",
            "episode_padding": 3,
            "remove_words": "1080p,简体",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "自动重命名规则已保存"
    assert response.json()["rule"]["episode_padding"] == 3


def test_preview_warns_when_episode_is_unknown(
    client: TestClient,
    db_session: Session,
) -> None:
    download = _create_download_with_files(db_session)

    response = client.post(f"/api/tasks/{download.id}/rename-preview")

    assert response.status_code == 200
    preview = next(
        item for item in response.json()["previews"] if item["original_name"] == "无法识别.mkv"
    )
    assert preview["confidence"] < 60
    assert preview["warning_message"] == "未能识别集数，请人工确认。"


def test_preview_marks_duplicate_target_name_as_conflict(
    client: TestClient,
    db_session: Session,
) -> None:
    download = _create_download_with_files(db_session)
    db_session.add(
        DownloadFile(
            download_task_id=download.id,
            file_index=3,
            name="另一个.S01E02.mkv",
            size=1_000_000_000,
            progress=1,
            file_type="video",
            selected=True,
            episode_number=2,
        )
    )
    db_session.commit()

    response = client.post(f"/api/tasks/{download.id}/rename-preview")

    assert response.status_code == 200
    conflicts = [item for item in response.json()["previews"] if item["conflict"]]
    assert conflicts
    assert conflicts[0]["warning_message"] == "目标文件名已存在，不能覆盖。"


def test_apply_rename_calls_provider_for_safe_previews(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    download = _create_download_with_files(db_session)
    client.post(f"/api/tasks/{download.id}/rename-preview")
    calls: list[dict[str, str]] = []

    def fake_rename_115_file(*, file_id: str, new_name: str) -> None:
        calls.append({"file_id": file_id, "new_name": new_name})

    monkeypatch.setattr("app.services.rename_service.rename_115_file", fake_rename_115_file)

    response = client.post(f"/api/tasks/{download.id}/rename-apply")

    assert response.status_code == 200
    assert response.json()["message"] == "重命名执行完成"
    assert calls[0]["new_name"] == "测试番剧 S01 - 02.mkv"
    assert response.json()["actions"][0]["status"] == "completed"


def test_apply_failure_writes_action_with_chinese_error(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    download = _create_download_with_files(db_session)
    client.post(f"/api/tasks/{download.id}/rename-preview")

    def fake_rename_115_file(*, file_id: str, new_name: str) -> None:
        raise RuntimeError("provider boom")

    monkeypatch.setattr("app.services.rename_service.rename_115_file", fake_rename_115_file)

    response = client.post(f"/api/tasks/{download.id}/rename-apply")

    assert response.status_code == 200
    failed = next(item for item in response.json()["actions"] if item["status"] == "failed")
    assert failed["error_message"] == "重命名失败：provider boom"


def test_apply_without_provider_reports_missing_115_rename(
    client: TestClient,
    db_session: Session,
) -> None:
    download = _create_download_with_files(db_session)
    client.post(f"/api/tasks/{download.id}/rename-preview")

    response = client.post(f"/api/tasks/{download.id}/rename-apply")

    assert response.status_code == 200
    assert response.json()["actions"][0]["error_message"] == "当前项目未发现可用的 115 重命名能力。"


def test_rollback_calls_provider_with_old_name(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    download = _create_download_with_files(db_session)
    client.post(f"/api/tasks/{download.id}/rename-preview")
    monkeypatch.setattr("app.services.rename_service.rename_115_file", lambda **_kwargs: None)
    action_response = client.post(f"/api/tasks/{download.id}/rename-apply")
    action_id = action_response.json()["actions"][0]["id"]
    calls: list[dict[str, str]] = []

    def fake_rollback(*, file_id: str, new_name: str) -> None:
        calls.append({"file_id": file_id, "new_name": new_name})

    monkeypatch.setattr("app.services.rename_service.rename_115_file", fake_rollback)

    response = client.post(f"/api/rename-actions/{action_id}/rollback")

    assert response.status_code == 200
    assert response.json()["message"] == "重命名动作已回滚"
    assert calls[0]["new_name"] == "测试.番剧.S01E02.mkv"


def test_refresh_completed_generates_preview_but_does_not_auto_execute_by_default(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    download = _create_download_with_files(db_session)
    client.put("/api/rename/rule", json={"enabled": True})
    monkeypatch.setattr(
        "app.services.download_service._settings_credentials",
        lambda _settings: ("http://127.0.0.1:8080", "admin", "password"),
    )
    monkeypatch.setattr(
        "app.services.download_service.get_torrent_status",
        lambda **_kwargs: {"status": "completed", "progress": 1.0},
    )
    calls: list[dict[str, str]] = []
    monkeypatch.setattr(
        "app.services.rename_service.rename_115_file",
        lambda **kwargs: calls.append(kwargs),
    )

    response = client.post(f"/api/downloads/{download.id}/refresh")

    assert response.status_code == 200
    assert response.json()["download"]["status"] == "completed"
    preview_response = client.get(f"/api/tasks/{download.id}/rename-preview")
    assert preview_response.json()["previews"]
    assert calls == []


def test_responses_do_not_expose_sensitive_header_values(
    client: TestClient,
    db_session: Session,
) -> None:
    download = _create_download_with_files(db_session)

    response = client.post(f"/api/tasks/{download.id}/rename-preview")
    serialized = response.text

    assert "Cookie" not in serialized
    assert "Token" not in serialized
    assert "Authorization" not in serialized

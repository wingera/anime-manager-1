from collections.abc import Generator

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


def test_tmdb_search_requires_api_key(client: TestClient) -> None:
    item_id = _create_source_item(client)

    response = client.post(f"/api/source-items/{item_id}/tmdb/search")

    assert response.status_code == 400
    assert response.json()["detail"] == "请先填写 TMDB API 密钥"


def test_save_match_for_source_item(client: TestClient) -> None:
    item_id = _create_source_item(client)

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
    data = response.json()
    assert data["message"] == "匹配信息已保存"
    assert data["match"]["source_item_id"] == item_id
    assert data["match"]["tmdb_id"] == 123
    assert data["match"]["episode_title"] == "第一集"


def test_repeated_save_match_updates_existing_record(client: TestClient) -> None:
    item_id = _create_source_item(client)
    first_payload = {
        "tmdb_id": 123,
        "title": "测试番剧",
        "original_title": "Original Test",
        "year": 2026,
        "season_number": 1,
        "episode_number": None,
        "episode_title": None,
        "match_score": 80,
        "status": "pending",
    }
    second_payload = {
        **first_payload,
        "tmdb_id": 456,
        "episode_number": 2,
        "episode_title": "第二集",
        "match_score": 95,
        "status": "confirmed",
    }

    first_response = client.put(f"/api/source-items/{item_id}/match", json=first_payload)
    second_response = client.put(f"/api/source-items/{item_id}/match", json=second_payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["match"]["id"] == second_response.json()["match"]["id"]
    assert second_response.json()["match"]["tmdb_id"] == 456
    assert second_response.json()["match"]["episode_number"] == 2


def test_list_matches_returns_saved_records(client: TestClient) -> None:
    item_id = _create_source_item(client)
    client.put(
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

    response = client.get("/api/matches")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "匹配列表获取成功"
    assert len(data["matches"]) == 1
    assert data["matches"][0]["source_item_id"] == item_id
    assert data["matches"][0]["title"] == "测试番剧"

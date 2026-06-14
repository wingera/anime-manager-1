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


def _create_source(client: TestClient) -> int:
    response = client.post(
        "/api/sources",
        json={
            "name": "用户授权来源",
            "url": "https://example.test/list",
            "source_type": "webpage",
            "enabled": False,
            "auth_note": "",
        },
    )
    assert response.status_code == 201
    return int(response.json()["source"]["id"])


def test_add_preview_items_to_resource_library(client: TestClient) -> None:
    source_id = _create_source(client)

    response = client.post(
        f"/api/sources/{source_id}/items",
        json={
            "items": [
                {
                    "title": "测试标题 S01E02 2026",
                    "url": "https://example.test/item",
                    "info_hash": "ABCDEF1234567890ABCDEF1234567890ABCDEF12",
                }
            ]
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "资源已加入资源库"
    assert data["created_count"] == 1
    assert data["skipped_count"] == 0
    assert data["items"][0]["info_hash"] == "abcdef1234567890abcdef1234567890abcdef12"
    assert data["items"][0]["magnet_uri"] == (
        "magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12"
    )


def test_duplicate_info_hash_is_skipped_when_adding_items(client: TestClient) -> None:
    source_id = _create_source(client)
    payload = {
        "items": [
            {
                "title": "第一条",
                "url": "https://example.test/one",
                "info_hash": "abcdef1234567890abcdef1234567890abcdef12",
            },
            {
                "title": "重复条目",
                "url": "https://example.test/two",
                "info_hash": "ABCDEF1234567890ABCDEF1234567890ABCDEF12",
            },
        ]
    }

    response = client.post(f"/api/sources/{source_id}/items", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["created_count"] == 1
    assert data["skipped_count"] == 1
    assert len(data["items"]) == 2

    list_response = client.get("/api/source-items")
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1


def test_invalid_info_hash_is_rejected_when_adding_items(client: TestClient) -> None:
    source_id = _create_source(client)

    response = client.post(
        f"/api/sources/{source_id}/items",
        json={"items": [{"title": "错误资源", "url": None, "info_hash": "abc123"}]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "资源指纹必须是 40 位十六进制字符串"

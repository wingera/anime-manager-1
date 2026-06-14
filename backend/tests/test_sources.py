from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models import SourceItem
from app.main import app
from app.services.source_service import create_source_item
from app.utils.info_hash import find_info_hashes, normalize_info_hash


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


def test_create_source_success(client: TestClient) -> None:
    response = client.post(
        "/api/sources",
        json={
            "name": "用户授权来源",
            "url": "https://example.test/list",
            "source_type": "webpage",
            "enabled": False,
            "auth_note": "",
            "fetch_interval_minutes": 60,
            "hash_pattern": "",
            "title_cleanup_rules": "",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "来源已创建"
    assert data["source"]["name"] == "用户授权来源"
    assert data["source"]["enabled"] is False


def test_enabled_source_requires_auth_note(client: TestClient) -> None:
    response = client.post(
        "/api/sources",
        json={
            "name": "缺少授权备注",
            "url": "https://example.test/list",
            "source_type": "webpage",
            "enabled": True,
            "auth_note": "",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "启用来源前必须填写授权备注"


def test_find_40_character_info_hash() -> None:
    found = find_info_hashes(
        "标题 ABCDEF1234567890ABCDEF1234567890ABCDEF12 "
        "以及重复 abcdef1234567890abcdef1234567890abcdef12"
    )

    assert found == ["abcdef1234567890abcdef1234567890abcdef12"]


def test_reject_non_40_character_info_hash() -> None:
    with pytest.raises(ValueError, match="资源指纹必须是 40 位十六进制字符串"):
        normalize_info_hash("abc123")


def test_duplicate_info_hash_does_not_create_duplicate_item(db_session: Session) -> None:
    source = create_source_item(
        db_session,
        source_id=1,
        title="第一条",
        url="https://example.test/one",
        info_hash="ABCDEF1234567890ABCDEF1234567890ABCDEF12",
    )
    duplicate = create_source_item(
        db_session,
        source_id=1,
        title="第二条",
        url="https://example.test/two",
        info_hash="abcdef1234567890abcdef1234567890abcdef12",
    )

    items = db_session.scalars(select(SourceItem)).all()
    assert source.id == duplicate.id
    assert len(items) == 1
    assert items[0].info_hash == "abcdef1234567890abcdef1234567890abcdef12"


def test_source_test_returns_preview_without_creating_items(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/api/sources",
        json={
            "name": "测试来源",
            "url": "https://example.test/list",
            "source_type": "webpage",
            "enabled": False,
        },
    )
    source_id = create_response.json()["source"]["id"]

    class FakeResponse:
        text = "<a href='/item'>测试标题 abcdef1234567890abcdef1234567890abcdef12</a>"

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.source_service.httpx.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    response = client.post(f"/api/sources/{source_id}/test")

    assert response.status_code == 200
    data = response.json()
    assert data["source_id"] == source_id
    assert data["found_count"] == 1
    assert data["items"] == [
        {
            "title": "测试标题 abcdef1234567890abcdef1234567890abcdef12",
            "url": "https://example.test/item",
            "info_hash": "abcdef1234567890abcdef1234567890abcdef12",
            "magnet_uri": "magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12",
        }
    ]
    assert db_session.scalars(select(SourceItem)).all() == []

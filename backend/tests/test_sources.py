from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.db.models import SourceItem, SourceSite
from app.main import app
from app.services.source_service import (
    _detail_urls_from_context,
    _extract_preview_context,
    create_source_item,
    preview_source_items,
)
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
            "published_at": None,
            "resource_group": None,
            "cover_image_url": None,
            "page_number": 1,
            "page_url": "https://example.test/list",
        }
    ]
    assert data["pagination"] == {
        "current_page": 1,
        "total_pages": 1,
        "pages": [{"page_number": 1, "url": "https://example.test/list"}],
    }
    assert data["warning_message"] is None
    assert db_session.scalars(select(SourceItem)).all() == []


def test_source_test_retries_transient_fetch_failure_without_creating_items(
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
    requested_urls: list[str] = []

    class FakeResponse:
        text = "<a href='/item'>测试标题 abcdef1234567890abcdef1234567890abcdef12</a>"

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, **_: object) -> FakeResponse:
        requested_urls.append(url)
        if len(requested_urls) < 4:
            raise httpx.ConnectError("连接临时中断")
        return FakeResponse()

    monkeypatch.setattr("app.services.source_service.httpx.get", fake_get)

    response = client.post(f"/api/sources/{source_id}/test")

    assert response.status_code == 200
    data = response.json()
    assert data["found_count"] == 1
    assert len(data["items"]) == 1
    assert data["pagination"]["total_pages"] == 1
    assert requested_urls == ["https://example.test/list"] * 4
    assert db_session.scalars(select(SourceItem)).all() == []


def test_source_test_does_not_scan_detail_pages_by_default(
    client: TestClient,
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
    requested_urls: list[str] = []

    class FakeResponse:
        text = '<article><a href="/detail">详情页标题</a></article>'

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, **_: object) -> FakeResponse:
        requested_urls.append(url)
        return FakeResponse()

    monkeypatch.setattr("app.services.source_service.httpx.get", fake_get)

    response = client.post(f"/api/sources/{source_id}/test")

    assert response.status_code == 200
    data = response.json()
    assert data["found_count"] == 0
    assert data["items"] == []
    assert data["pagination"]["total_pages"] == 1
    assert requested_urls == ["https://example.test/list"]


def test_source_test_scans_enabled_same_site_detail_pages_without_creating_items(
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
            "scan_detail_pages": True,
        },
    )
    assert create_response.status_code == 201
    source_id = create_response.json()["source"]["id"]
    assert create_response.json()["source"]["scan_detail_pages"] is True
    requested_urls: list[str] = []

    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, **_: object) -> FakeResponse:
        requested_urls.append(url)
        if url == "https://example.test/list":
            return FakeResponse('<article><a href="/detail">详情页标题</a></article>')
        if url == "https://example.test/detail":
            return FakeResponse(
                """
                <html>
                  <head><title>详情页标题</title></head>
                  <body>
                    <article>
                      <a href="/tag/noise">详情页标签</a>
                      <time datetime="2026-06-02T08:00:00Z">2026-06-02</time>
                      <p>资源指纹 abcdef1234567890abcdef1234567890abcdef12</p>
                    </article>
                  </body>
                </html>
                """
            )
        raise AssertionError(f"不应请求其他地址：{url}")

    monkeypatch.setattr("app.services.source_service.httpx.get", fake_get)

    response = client.post(f"/api/sources/{source_id}/test")

    assert response.status_code == 200
    data = response.json()
    assert data["found_count"] == 1
    assert data["items"] == [
        {
            "title": "详情页标题",
            "url": "https://example.test/detail",
            "info_hash": "abcdef1234567890abcdef1234567890abcdef12",
            "magnet_uri": "magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12",
            "published_at": "2026-06-02T08:00:00Z",
            "resource_group": None,
            "cover_image_url": None,
            "page_number": 1,
            "page_url": "https://example.test/detail",
        }
    ]
    assert data["pagination"]["total_pages"] == 1
    assert requested_urls == ["https://example.test/list", "https://example.test/detail"]
    assert db_session.scalars(select(SourceItem)).all() == []


def test_detail_page_candidates_prefer_article_primary_links() -> None:
    source = SourceSite(id=1, name="授权网页", url="https://example.test/list/index.html")
    html = """
    <html>
      <body>
        <nav>
          <a href="/list/">父级目录</a>
          <a href="/category/anime">动画分类</a>
          <a href="/tag/popular">热门标签</a>
        </nav>
        <article>
          <h2><a href="/posts/one">第一篇详情</a></h2>
          <p>这里是足够长的摘要文本，用于说明这个区块更像一篇文章而不是导航。</p>
          <a href="/tag/story">作品标签</a>
          <a href="/author/editor">作者</a>
        </article>
        <article>
          <h2><a href="/posts/two">第二篇详情</a></h2>
          <p>这里也是一段正文摘要，用于构成另一个可扫描的文章候选。</p>
        </article>
      </body>
    </html>
    """

    urls = _detail_urls_from_context(source, _extract_preview_context(html))

    assert urls[:2] == [
        "https://example.test/posts/one",
        "https://example.test/posts/two",
    ]
    assert "https://example.test/category/anime" not in urls
    assert "https://example.test/list/" not in urls
    assert "https://example.test/tag/popular" not in urls
    assert "https://example.test/tag/story" not in urls
    assert "https://example.test/author/editor" not in urls


def test_detail_page_candidates_ignore_pagination_query_links() -> None:
    source = SourceSite(id=1, name="授权网页", url="https://example.test/list")
    html = """
    <html>
      <body>
        <a href="?paged=2">下一页</a>
        <a href="/posts/one">第一篇详情</a>
        <a href="?page=3">第 3 页</a>
      </body>
    </html>
    """

    urls = _detail_urls_from_context(source, _extract_preview_context(html))

    assert urls == ["https://example.test/posts/one"]


def test_detail_page_scan_collects_multiple_detail_pages_on_selected_page(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/api/sources",
        json={
            "name": "测试来源",
            "url": "https://example.test/list",
            "source_type": "webpage",
            "enabled": False,
            "scan_detail_pages": True,
        },
    )
    source_id = create_response.json()["source"]["id"]
    requested_urls: list[str] = []

    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, **_: object) -> FakeResponse:
        requested_urls.append(url)
        if url == "https://example.test/list":
            return FakeResponse(
                """
                <article>
                  <a href="/detail-one">第一篇详情</a>
                  <p>这里是第一篇文章摘要。</p>
                </article>
                <article>
                  <a href="/detail-two">第二篇详情</a>
                  <p>这里是第二篇文章摘要。</p>
                </article>
                """
            )
        if url == "https://example.test/detail-one":
            return FakeResponse(
                """
                <html>
                  <head><title>第一篇详情</title></head>
                  <body>abcdef1234567890abcdef1234567890abcdef12</body>
                </html>
                """
            )
        if url == "https://example.test/detail-two":
            return FakeResponse(
                """
                <html>
                  <head><title>第二篇详情</title></head>
                  <body>1234567890abcdef1234567890abcdef12345678</body>
                </html>
                """
            )
        raise AssertionError(f"不应请求其他地址：{url}")

    monkeypatch.setattr("app.services.source_service.httpx.get", fake_get)

    response = client.post(f"/api/sources/{source_id}/test")

    assert response.status_code == 200
    assert response.json()["found_count"] == 2
    assert [item["title"] for item in response.json()["items"]] == ["第一篇详情", "第二篇详情"]
    assert requested_urls == [
        "https://example.test/list",
        "https://example.test/detail-one",
        "https://example.test/detail-two",
    ]


def test_detail_page_scan_reports_failures_and_uses_current_archive_category(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_response = client.post(
        "/api/sources",
        json={
            "name": "动画来源",
            "url": "https://example.test/wp/anime.html",
            "source_type": "webpage",
            "enabled": False,
            "scan_detail_pages": True,
        },
    )
    source_id = create_response.json()["source"]["id"]
    requested_urls: list[str] = []

    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, **_: object) -> FakeResponse:
        requested_urls.append(url)
        if url == "https://example.test/wp/anime.html":
            return FakeResponse(
                """
                <main>
                  <h1>分类目录归档：动画</h1>
                  <article>
                    <h2><a href="/wp/anime-ok.html">动画条目</a></h2>
                    <p>这是动画归档里的正文摘要。</p>
                    <p>发表在 <a href="/wp/anime.html">动画</a></p>
                  </article>
                  <article>
                    <h2><a href="/wp/anime-fail.html">失败条目</a></h2>
                    <p>这条详情页暂时无法读取。</p>
                    <p>发表在 <a href="/wp/anime.html">动画</a></p>
                  </article>
                </main>
                <aside>
                  <h3>漫画点赞榜</h3>
                  <a href="/wp/comic-sidebar.html">不应扫描的侧栏资源</a>
                </aside>
                """
            )
        if url == "https://example.test/wp/anime-ok.html":
            return FakeResponse(
                """
                <html>
                  <head><title>动画条目</title></head>
                  <body>abcdef1234567890abcdef1234567890abcdef12</body>
                </html>
                """
            )
        if url == "https://example.test/wp/anime-fail.html":
            raise httpx.ReadTimeout("读取超时")
        raise AssertionError(f"不应请求其他地址：{url}")

    monkeypatch.setattr("app.services.source_service.httpx.get", fake_get)

    response = client.post(f"/api/sources/{source_id}/test")

    assert response.status_code == 200
    data = response.json()
    assert data["found_count"] == 1
    assert [item["url"] for item in data["items"]] == ["https://example.test/wp/anime-ok.html"]
    assert data["failed_pages"] == [
        {
            "url": "https://example.test/wp/anime-fail.html",
            "title": "失败条目",
            "message": "详情页读取失败，请稍后重试",
        }
    ]
    assert requested_urls == [
        "https://example.test/wp/anime.html",
        "https://example.test/wp/anime-ok.html",
        "https://example.test/wp/anime-fail.html",
    ]


def test_source_test_discovers_pagination_without_scanning_other_pages(
    client: TestClient,
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
    requested_urls: list[str] = []

    class FakeResponse:
        text = """
        <html>
          <body>
            <nav>
              <a href="/list?page=2">2</a>
              <a href="/list?page=3">3</a>
            </nav>
            <article>
              <h2><a href="/posts/one">第一页资源</a></h2>
              <p>abcdef1234567890abcdef1234567890abcdef12</p>
            </article>
          </body>
        </html>
        """

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, **_: object) -> FakeResponse:
        requested_urls.append(url)
        if url != "https://example.test/list":
            raise AssertionError(f"首次测试不应自动扫描分页：{url}")
        return FakeResponse()

    monkeypatch.setattr("app.services.source_service.httpx.get", fake_get)

    response = client.post(f"/api/sources/{source_id}/test")

    assert response.status_code == 200
    data = response.json()
    assert data["found_count"] == 1
    assert data["pagination"] == {
        "current_page": 1,
        "total_pages": 3,
        "pages": [
            {"page_number": 1, "url": "https://example.test/list"},
            {"page_number": 2, "url": "https://example.test/list?page=2"},
            {"page_number": 3, "url": "https://example.test/list?page=3"},
        ],
    }
    assert requested_urls == ["https://example.test/list"]


def test_source_test_does_not_treat_numeric_article_links_as_pages(
    client: TestClient,
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
        text = """
        <html>
          <body>
            <a href="/posts/102537">第 2 集详情</a>
            <a href="/list/page/4">4</a>
            <article>abcdef1234567890abcdef1234567890abcdef12</article>
          </body>
        </html>
        """

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.source_service.httpx.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    response = client.post(f"/api/sources/{source_id}/test")

    assert response.status_code == 200
    assert response.json()["pagination"] == {
        "current_page": 1,
        "total_pages": 4,
        "pages": [
            {"page_number": 1, "url": "https://example.test/list"},
            {"page_number": 4, "url": "https://example.test/list/page/4"},
        ],
    }


def test_source_test_can_scan_selected_page_only(
    client: TestClient,
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
    requested_urls: list[str] = []

    class FakeResponse:
        def __init__(self, text: str) -> None:
            self.text = text

        def raise_for_status(self) -> None:
            return None

    def fake_get(url: str, **_: object) -> FakeResponse:
        requested_urls.append(url)
        if url == "https://example.test/list":
            return FakeResponse(
                """
                <a href="/list?page=2">2</a>
                <a href="/list?page=3">3</a>
                <article>第一页 abcdef1234567890abcdef1234567890abcdef12</article>
                """
            )
        if url == "https://example.test/list?page=3":
            return FakeResponse(
                """
                <article>第三页 1234567890abcdef1234567890abcdef12345678</article>
                """
            )
        raise AssertionError(f"不应请求其他分页：{url}")

    monkeypatch.setattr("app.services.source_service.httpx.get", fake_get)

    response = client.post(f"/api/sources/{source_id}/test", json={"page_number": 3})

    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["current_page"] == 3
    assert data["found_count"] == 1
    assert data["items"][0]["title"] == "第三页 1234567890abcdef1234567890abcdef12345678"
    assert data["items"][0]["page_number"] == 3
    assert data["items"][0]["page_url"] == "https://example.test/list?page=3"
    assert requested_urls == ["https://example.test/list", "https://example.test/list?page=3"]


def test_generic_preview_groups_hashes_and_extracts_cover_image() -> None:
    source = SourceSite(id=1, name="授权网页", url="https://example.test/list")
    html = """
    <article>
      <h2><a href="/posts/one">资源合集</a></h2>
      <img src="/covers/one.jpg" alt="封面">
      <p>中文CG集</p>
      <p>86AA642BBE379663D0201832D50C98B46B76AFCD</p>
      <p>B13AD56CED684203866CE853010A94D2881BE814</p>
      <p>动画</p>
      <p>45fcc410ee76944fbdb18dcb5110a7a0aafe63d6</p>
    </article>
    """

    found_count, items, warning_message, pagination = preview_source_items(source, html)

    assert found_count == 3
    assert warning_message is None
    assert pagination.total_pages == 1
    assert [item.resource_group for item in items] == ["中文CG集", "中文CG集", "动画"]
    assert [item.cover_image_url for item in items] == [
        "https://example.test/covers/one.jpg",
        "https://example.test/covers/one.jpg",
        "https://example.test/covers/one.jpg",
    ]


def test_generic_preview_ignores_noisy_resource_group_candidates() -> None:
    source = SourceSite(id=1, name="授权网页", url="https://example.test/list")
    html = """
    <article>
      <p>平均評価</p>
      <p>abcdef1234567890abcdef1234567890abcdef12</p>
      <p>5.97GB</p>
      <p>1234567890abcdef1234567890abcdef12345678</p>
      <p>MONSTER_06.zip</p>
      <p>1111111111111111111111111111111111111111</p>
      <p>信じていた母のヒミツを知った息子棒はっ……</p>
      <p>2222222222222222222222222222222222222222</p>
      <p>中文(简体字)、日语、英语</p>
      <p>3333333333333333333333333333333333333333</p>
      <p>MOTION引以为傲的高质量动态动画</p>
      <p>4444444444444444444444444444444444444444</p>
    </article>
    """

    found_count, items, warning_message, _pagination = preview_source_items(source, html)

    assert found_count == 6
    assert warning_message is None
    assert [item.resource_group for item in items] == [None, None, None, None, None, None]


def test_generic_html_preview_extracts_article_title_link_time_and_info_hash() -> None:
    source = SourceSite(id=1, name="授权网页", url="https://example.test/list")
    html = """
    <html>
      <head><title>授权来源列表</title></head>
      <body>
        <article>
          <h2><a href="/posts/one">第一集更新</a></h2>
          <time datetime="2026-06-01T12:30:00Z">2026-06-01</time>
          <p>资源指纹 abcdef1234567890abcdef1234567890abcdef12</p>
        </article>
      </body>
    </html>
    """

    found_count, items, warning_message, _pagination = preview_source_items(source, html)

    assert found_count == 1
    assert warning_message is None
    assert len(items) == 1
    assert items[0].title == "第一集更新"
    assert items[0].url == "https://example.test/posts/one"
    assert items[0].info_hash == "abcdef1234567890abcdef1234567890abcdef12"
    assert items[0].published_at is not None
    assert items[0].published_at.isoformat() == "2026-06-01T12:30:00+00:00"


def test_generic_html_preview_deduplicates_repeated_info_hash() -> None:
    source = SourceSite(id=1, name="授权网页", url="https://example.test/list")
    html = """
    <article>
      <a href="/one">第一条 abcdef1234567890abcdef1234567890abcdef12</a>
      <p>重复 ABCDEF1234567890ABCDEF1234567890ABCDEF12</p>
    </article>
    """

    found_count, items, warning_message, _pagination = preview_source_items(source, html)

    assert found_count == 1
    assert warning_message is None
    assert [item.info_hash for item in items] == [
        "abcdef1234567890abcdef1234567890abcdef12"
    ]


def test_generic_html_preview_returns_warning_for_configured_high_risk_keyword() -> None:
    source = SourceSite(id=1, name="授权网页", url="https://example.test/list?tag=adult")
    html = """
    <html>
      <head><title>用户授权 adult 列表</title></head>
      <body>
        <article><a href="/one">测试 abcdef1234567890abcdef1234567890abcdef12</a></article>
      </body>
    </html>
    """

    found_count, items, warning_message, _pagination = preview_source_items(source, html)

    assert found_count == 1
    assert len(items) == 1
    assert warning_message == "该来源可能包含高风险内容，请确认你拥有合法访问和整理权限。"


def test_generic_html_preview_ignores_non_40_character_info_hash() -> None:
    source = SourceSite(id=1, name="授权网页", url="https://example.test/list")
    html = '<a href="/bad">错误资源 abcdef1234567890abcdef1234567890abcdef1</a>'

    found_count, items, warning_message, _pagination = preview_source_items(source, html)

    assert found_count == 0
    assert items == []
    assert warning_message is None


def test_import_source_items_requires_permission_confirmation(client: TestClient) -> None:
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

    response = client.post(
        f"/api/sources/{source_id}/items",
        json={
            "permission_confirmed": False,
            "items": [
                {
                    "title": "测试标题",
                    "url": "https://example.test/item",
                    "info_hash": "abcdef1234567890abcdef1234567890abcdef12",
                    "published_at": "2026-06-01T12:30:00Z",
                }
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "加入资源库前必须确认合法访问、下载和整理权限"

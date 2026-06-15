from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.db.models import SourceItem, SourceSite
from app.schemas.sources import SourcePreviewItem, SourceSiteCreate, SourceSiteUpdate
from app.utils.info_hash import build_magnet_uri, find_info_hashes, normalize_info_hash

SOURCE_TEST_ERROR = "来源测试失败，请检查地址是否可访问"
AUTH_NOTE_REQUIRED_ERROR = "启用来源前必须填写授权备注"
HIGH_RISK_SOURCE_WARNING = "该来源可能包含高风险内容，请确认你拥有合法访问和整理权限。"
ARTICLE_CONTAINER_TAGS = {"article", "li", "section", "div"}


class SourceTestError(RuntimeError):
    pass


@dataclass(frozen=True)
class HtmlLink:
    text: str
    href: str | None


@dataclass
class HtmlBlock:
    text_parts: list[str]
    links: list[HtmlLink]
    published_at: datetime | None = None

    @property
    def text(self) -> str:
        return _normalize_text(" ".join(self.text_parts))


@dataclass(frozen=True)
class HtmlPreviewContext:
    links: list[HtmlLink]
    blocks: list[HtmlBlock]
    page_title: str
    metadata_text: str
    visible_text: str


class _GenericHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[HtmlLink] = []
        self.blocks: list[HtmlBlock] = []
        self.page_title_parts: list[str] = []
        self.metadata_parts: list[str] = []
        self.visible_text_parts: list[str] = []
        self._block_stack: list[HtmlBlock] = []
        self._active_href: str | None = None
        self._active_text: list[str] = []
        self._active_time_text: list[str] | None = None
        self._active_time_datetime: str | None = None
        self._in_title = False

    @property
    def context(self) -> HtmlPreviewContext:
        return HtmlPreviewContext(
            links=self.links,
            blocks=self.blocks,
            page_title=_normalize_text(" ".join(self.page_title_parts)),
            metadata_text=_normalize_text(" ".join(self.metadata_parts)),
            visible_text=_normalize_text(" ".join(self.visible_text_parts)),
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        if normalized_tag == "title":
            self._in_title = True
        if normalized_tag == "meta":
            self._record_metadata(attr_map)
        if normalized_tag in ARTICLE_CONTAINER_TAGS:
            self._block_stack.append(HtmlBlock(text_parts=[], links=[]))
        if normalized_tag == "a":
            self._active_href = attr_map.get("href")
            self._active_text = []
        if normalized_tag == "time":
            self._active_time_text = []
            self._active_time_datetime = attr_map.get("datetime")

    def handle_data(self, data: str) -> None:
        if _normalize_text(data) == "":
            return
        self.visible_text_parts.append(data)
        for block in self._block_stack:
            block.text_parts.append(data)
        if self._in_title:
            self.page_title_parts.append(data)
        if self._active_href is not None:
            self._active_text.append(data)
        if self._active_time_text is not None:
            self._active_time_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag == "title":
            self._in_title = False
        if normalized_tag == "a":
            self._finish_link()
            return
        if normalized_tag == "time":
            self._finish_time()
            return
        if normalized_tag in ARTICLE_CONTAINER_TAGS and self._block_stack:
            self.blocks.append(self._block_stack.pop())

    def _record_metadata(self, attr_map: dict[str, str]) -> None:
        name = attr_map.get("name", "").lower()
        prop = attr_map.get("property", "").lower()
        content = attr_map.get("content")
        if not content:
            return
        metadata_fields = {
            "keywords",
            "description",
            "tag",
            "tags",
            "article:tag",
            "og:title",
        }
        if name in metadata_fields or prop in metadata_fields:
            self.metadata_parts.append(content)
        if name == "article:published_time" or prop == "article:published_time":
            published_at = _parse_published_at(content)
            if published_at is not None and self._block_stack:
                self._block_stack[-1].published_at = published_at

    def _finish_link(self) -> None:
        if self._active_href is None:
            return
        title = _normalize_text("".join(self._active_text))
        link = HtmlLink(text=title, href=self._active_href)
        self.links.append(link)
        for block in self._block_stack:
            block.links.append(link)
        self._active_href = None
        self._active_text = []

    def _finish_time(self) -> None:
        if self._active_time_text is None:
            return
        time_text = _normalize_text(" ".join(self._active_time_text))
        published_at = _parse_published_at(self._active_time_datetime or time_text)
        if published_at is not None and self._block_stack:
            self._block_stack[-1].published_at = published_at
        self._active_time_text = None
        self._active_time_datetime = None


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _parse_published_at(value: str) -> datetime | None:
    normalized = value.strip()
    if normalized == "":
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _validate_source(
    payload: SourceSiteCreate | SourceSiteUpdate,
    current: SourceSite | None = None,
) -> None:
    enabled = (
        payload.enabled
        if payload.enabled is not None
        else current.enabled
        if current
        else False
    )
    auth_note = (
        payload.auth_note
        if payload.auth_note is not None
        else current.auth_note
        if current
        else ""
    )
    if enabled and auth_note.strip() == "":
        raise ValueError(AUTH_NOTE_REQUIRED_ERROR)


def list_sources(db: Session) -> list[SourceSite]:
    return list(
        db.scalars(select(SourceSite).order_by(SourceSite.created_at.desc(), SourceSite.id.desc()))
    )


def get_source(db: Session, source_id: int) -> SourceSite | None:
    return db.get(SourceSite, source_id)


def create_source(db: Session, payload: SourceSiteCreate) -> SourceSite:
    _validate_source(payload)
    source = SourceSite(
        name=payload.name.strip(),
        url=payload.url.strip(),
        source_type=payload.source_type,
        enabled=payload.enabled,
        auth_note=payload.auth_note.strip(),
        fetch_interval_minutes=payload.fetch_interval_minutes,
        hash_pattern=payload.hash_pattern.strip(),
        title_cleanup_rules=payload.title_cleanup_rules.strip(),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def update_source(db: Session, source: SourceSite, payload: SourceSiteUpdate) -> SourceSite:
    _validate_source(payload, source)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(source, field, value)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def delete_source(db: Session, source: SourceSite) -> None:
    db.execute(delete(SourceItem).where(SourceItem.source_id == source.id))
    db.delete(source)
    db.commit()


def create_source_item(
    db: Session,
    *,
    source_id: int,
    title: str,
    url: str | None,
    info_hash: str,
    published_at: datetime | None = None,
) -> SourceItem:
    normalized_hash = normalize_info_hash(info_hash)
    existing = db.scalar(select(SourceItem).where(SourceItem.info_hash == normalized_hash))
    if existing is not None:
        return existing

    item = SourceItem(
        source_id=source_id,
        title=title.strip(),
        url=url.strip() if url else None,
        info_hash=normalized_hash,
        magnet_uri=build_magnet_uri(normalized_hash),
        published_at=published_at,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def import_source_items(
    db: Session,
    *,
    source_id: int,
    items: list[tuple[str, str | None, str, datetime | None]],
) -> tuple[int, int, list[SourceItem]]:
    created_count = 0
    skipped_count = 0
    result_items: list[SourceItem] = []

    for title, url, info_hash, published_at in items:
        normalized_hash = normalize_info_hash(info_hash)
        existing = db.scalar(select(SourceItem).where(SourceItem.info_hash == normalized_hash))
        if existing is not None:
            skipped_count += 1
            result_items.append(existing)
            continue

        item = SourceItem(
            source_id=source_id,
            title=title.strip(),
            url=url.strip() if url else None,
            info_hash=normalized_hash,
            magnet_uri=build_magnet_uri(normalized_hash),
            published_at=published_at,
        )
        db.add(item)
        db.flush()
        db.refresh(item)
        created_count += 1
        result_items.append(item)

    db.commit()
    for item in result_items:
        db.refresh(item)
    return created_count, skipped_count, result_items


def list_source_items(db: Session) -> list[SourceItem]:
    return list(
        db.scalars(select(SourceItem).order_by(SourceItem.created_at.desc(), SourceItem.id.desc()))
    )


def _extract_preview_context(html: str) -> HtmlPreviewContext:
    parser = _GenericHtmlParser()
    parser.feed(html)
    return parser.context


def _find_link_for_hash(links: list[HtmlLink], info_hash: str) -> HtmlLink | None:
    for link in links:
        hash_in_text = info_hash in link.text.lower()
        hash_in_href = link.href is not None and info_hash in link.href.lower()
        if hash_in_text or hash_in_href:
            return link
    return None


def _find_block_for_hash(blocks: list[HtmlBlock], info_hash: str) -> HtmlBlock | None:
    matching_blocks = [block for block in blocks if info_hash in block.text.lower()]
    if not matching_blocks:
        return None
    return min(matching_blocks, key=lambda block: (len(block.text), 0 if block.links else 1))


def _first_title_link(links: list[HtmlLink]) -> HtmlLink | None:
    for link in links:
        if link.text:
            return link
    return links[0] if links else None


def _build_warning_message(source: SourceSite, context: HtmlPreviewContext) -> str | None:
    settings = get_settings()
    haystack = " ".join(
        [
            source.url,
            context.page_title,
            context.metadata_text,
            context.visible_text,
        ]
    ).lower()
    for keyword in settings.high_risk_source_keywords:
        normalized_keyword = keyword.strip().lower()
        if normalized_keyword and normalized_keyword in haystack:
            return HIGH_RISK_SOURCE_WARNING
    return None


def preview_source_items(
    source: SourceSite,
    html: str,
) -> tuple[int, list[SourcePreviewItem], str | None]:
    info_hashes = find_info_hashes(html)
    context = _extract_preview_context(html)
    previews: list[SourcePreviewItem] = []

    for index, info_hash in enumerate(info_hashes[:20], start=1):
        block = _find_block_for_hash(context.blocks, info_hash)
        link = None
        published_at = None
        if block is not None:
            link = _find_link_for_hash(block.links, info_hash) or _first_title_link(block.links)
            published_at = block.published_at
        if link is None:
            link = _find_link_for_hash(context.links, info_hash)
        title = link.text if link and link.text else context.page_title or f"资源指纹 {index}"
        item_url = urljoin(source.url, link.href) if link and link.href else None
        previews.append(
            SourcePreviewItem(
                title=title,
                url=item_url,
                info_hash=info_hash,
                magnet_uri=build_magnet_uri(info_hash),
                published_at=published_at,
            )
        )

    return len(info_hashes), previews, _build_warning_message(source, context)


def test_source(db: Session, source: SourceSite) -> tuple[int, list[SourcePreviewItem], str | None]:
    try:
        response = httpx.get(source.url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SourceTestError(SOURCE_TEST_ERROR) from exc

    source.last_checked_at = datetime.utcnow()
    db.add(source)
    db.commit()
    return preview_source_items(source, response.text)

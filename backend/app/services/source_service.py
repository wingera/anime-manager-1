import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, unquote, urldefrag, urljoin, urlparse

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.db.models import SourceItem, SourceSite
from app.schemas.sources import (
    SourcePagination,
    SourcePaginationPage,
    SourcePreviewItem,
    SourceScanFailure,
    SourceSiteCreate,
    SourceSiteUpdate,
)
from app.utils.info_hash import build_magnet_uri, find_info_hashes, normalize_info_hash

SOURCE_TEST_ERROR = "来源测试失败，请检查地址是否可访问"
DETAIL_PAGE_FETCH_FAILED = "详情页读取失败，请稍后重试"
AUTH_NOTE_REQUIRED_ERROR = "启用来源前必须填写授权备注"
HIGH_RISK_SOURCE_WARNING = "该来源可能包含高风险内容，请确认你拥有合法访问和整理权限。"
ARTICLE_CONTAINER_TAGS = {"article", "li", "section", "div"}
PREVIEW_ITEM_LIMIT = 20
SOURCE_FETCH_TIMEOUT_SECONDS = 10.0
SOURCE_FETCH_ATTEMPTS = 4
ARTICLE_BLOCK_MIN_TEXT_LENGTH = 20
LISTING_PATH_SEGMENTS = {
    "author",
    "authors",
    "category",
    "categories",
    "feed",
    "login",
    "page",
    "search",
    "tag",
    "tags",
    "wp-admin",
}
PAGINATION_QUERY_KEYS = {
    "page",
    "page_no",
    "page_number",
    "pageno",
    "paged",
}
MAX_PAGINATION_PAGE_NUMBER = 1000
RESOURCE_GROUP_MAX_LENGTH = 80
RESOURCE_GROUP_LABEL_MAX_LENGTH = 12
RESOURCE_GROUP_HASH_WINDOW = 120
ARCHIVE_CATEGORY_RE = re.compile(r"分类目录归档[:：]\s*([^\s，。|]+)")
INFO_HASH_RE = re.compile(r"\b[0-9a-fA-F]{40}\b")
DATE_LIKE_RE = re.compile(r"^\d{4}[-/年]\d{1,2}([-/月]\d{1,2}日?)?$")
FILE_SIZE_LIKE_RE = re.compile(r"^\d+(\.\d+)?\s*(b|kb|mb|gb|tb|kib|mib|gib|tib)$", re.IGNORECASE)
FILE_NAME_LIKE_RE = re.compile(
    r"^[^\s]+\.(zip|7z|rar|torrent|txt|jpg|jpeg|png|gif|mp4|mkv|avi)$",
    re.IGNORECASE,
)
RESOURCE_GROUP_KEYWORDS = {
    "anime",
    "audio",
    "cg",
    "comic",
    "game",
    "image",
    "images",
    "manga",
    "movie",
    "ova",
    "picture",
    "video",
    "中文字幕",
    "动画",
    "合集",
    "同人",
    "图集",
    "圖片",
    "图片",
    "字幕",
    "漫畫",
    "漫画",
    "游戏",
    "影片",
    "音声",
    "音频",
}
GENERIC_RESOURCE_GROUP_LABELS = {
    "hash",
    "info_hash",
    "magnet",
    "btih",
    "review",
    "reviews",
    "资源",
    "资源指纹",
    "磁力",
    "哈希",
    "查看评论",
    "评论",
    "レビュー",
    "レビューを見る",
}


class SourceTestError(RuntimeError):
    pass


@dataclass(frozen=True)
class HtmlLink:
    text: str
    href: str | None


@dataclass(frozen=True)
class HtmlImage:
    src: str
    alt: str


@dataclass
class HtmlBlock:
    text_parts: list[str]
    links: list[HtmlLink]
    images: list[HtmlImage]
    tag_name: str
    classes: set[str]
    published_at: datetime | None = None

    @property
    def text(self) -> str:
        return _normalize_text(" ".join(self.text_parts))


@dataclass(frozen=True)
class HtmlPreviewContext:
    links: list[HtmlLink]
    images: list[HtmlImage]
    blocks: list[HtmlBlock]
    page_title: str
    metadata_text: str
    visible_text: str
    published_at: datetime | None


@dataclass(frozen=True)
class DetailPageCandidate:
    url: str
    title: str | None


class _GenericHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[HtmlLink] = []
        self.images: list[HtmlImage] = []
        self.blocks: list[HtmlBlock] = []
        self.page_title_parts: list[str] = []
        self.metadata_parts: list[str] = []
        self.visible_text_parts: list[str] = []
        self.published_at: datetime | None = None
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
            images=self.images,
            blocks=self.blocks,
            page_title=_normalize_text(" ".join(self.page_title_parts)),
            metadata_text=_normalize_text(" ".join(self.metadata_parts)),
            visible_text=_normalize_text(" ".join(self.visible_text_parts)),
            published_at=self.published_at,
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        attr_map = {key.lower(): value for key, value in attrs if value is not None}
        if normalized_tag == "title":
            self._in_title = True
        if normalized_tag == "meta":
            self._record_metadata(attr_map)
        if normalized_tag in ARTICLE_CONTAINER_TAGS:
            self._block_stack.append(
                HtmlBlock(
                    text_parts=[],
                    links=[],
                    images=[],
                    tag_name=normalized_tag,
                    classes=set(attr_map.get("class", "").split()),
                )
            )
        if normalized_tag == "a":
            self._active_href = attr_map.get("href")
            self._active_text = []
        if normalized_tag == "img":
            self._record_image(attr_map)
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
            self._record_published_at(published_at)

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

    def _record_image(self, attr_map: dict[str, str]) -> None:
        src = attr_map.get("src") or attr_map.get("data-src") or attr_map.get("data-original")
        if src is None or src.strip() == "":
            return
        image = HtmlImage(src=src.strip(), alt=_normalize_text(attr_map.get("alt", "")))
        self.images.append(image)
        for block in self._block_stack:
            block.images.append(image)

    def _finish_time(self) -> None:
        if self._active_time_text is None:
            return
        time_text = _normalize_text(" ".join(self._active_time_text))
        published_at = _parse_published_at(self._active_time_datetime or time_text)
        self._record_published_at(published_at)
        self._active_time_text = None
        self._active_time_datetime = None

    def _record_published_at(self, published_at: datetime | None) -> None:
        if published_at is None:
            return
        if self.published_at is None:
            self.published_at = published_at
        if self._block_stack:
            self._block_stack[-1].published_at = published_at


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
        scan_detail_pages=payload.scan_detail_pages,
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


def _build_warning_message(source: SourceSite, contexts: list[HtmlPreviewContext]) -> str | None:
    settings = get_settings()
    haystack_parts = [source.url]
    for context in contexts:
        haystack_parts.extend([context.page_title, context.metadata_text, context.visible_text])
    haystack = " ".join(haystack_parts).lower()
    for keyword in settings.high_risk_source_keywords:
        normalized_keyword = keyword.strip().lower()
        if normalized_keyword and normalized_keyword in haystack:
            return HIGH_RISK_SOURCE_WARNING
    return None


def _fetch_source_url(url: str, *, attempts: int = 1) -> httpx.Response:
    normalized_attempts = max(1, attempts)
    for attempt in range(1, normalized_attempts + 1):
        try:
            response = httpx.get(
                url,
                timeout=SOURCE_FETCH_TIMEOUT_SECONDS,
                follow_redirects=True,
            )
            response.raise_for_status()
            return response
        except httpx.TransportError:
            if attempt == normalized_attempts:
                raise
    raise SourceTestError(SOURCE_TEST_ERROR)


def _normalize_same_site_url(base_url: str, href: str | None) -> str | None:
    if href is None or href.strip() == "":
        return None
    resolved, _fragment = urldefrag(urljoin(base_url, href.strip()))
    parsed = urlparse(resolved)
    base = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != base.netloc:
        return None
    return resolved


def _page_number_from_link(link: HtmlLink, resolved_url: str) -> int | None:
    parsed = urlparse(resolved_url)
    query_values = {
        key.strip().lower(): value.strip()
        for key, value in parse_qsl(parsed.query)
        if value.strip().isdigit()
    }
    for key in PAGINATION_QUERY_KEYS:
        value = query_values.get(key)
        if value is not None:
            return _safe_page_number(value)

    path_segments = [
        segment.strip().lower()
        for segment in parsed.path.split("/")
        if segment.strip()
    ]
    for index, segment in enumerate(path_segments[:-1]):
        if segment == "page":
            return _safe_page_number(path_segments[index + 1])

    return None


def _safe_page_number(value: str) -> int | None:
    normalized = value.strip()
    if not normalized.isdigit():
        return None
    page_number = int(normalized)
    if page_number < 1 or page_number > MAX_PAGINATION_PAGE_NUMBER:
        return None
    return page_number


def _build_pagination(
    *,
    source: SourceSite,
    context: HtmlPreviewContext,
    current_page: int = 1,
) -> SourcePagination:
    pages: dict[int, str] = {1: source.url}
    for link in context.links:
        resolved_url = _normalize_same_site_url(source.url, link.href)
        if resolved_url is None:
            continue
        page_number = _page_number_from_link(link, resolved_url)
        if page_number is None:
            continue
        pages.setdefault(page_number, resolved_url)

    if current_page not in pages:
        pages[current_page] = source.url

    ordered_pages = [
        SourcePaginationPage(page_number=page_number, url=pages[page_number])
        for page_number in sorted(pages)
    ]
    return SourcePagination(
        current_page=current_page,
        total_pages=max(pages),
        pages=ordered_pages,
    )


def _pagination_url_for_page(pagination: SourcePagination, page_number: int) -> str | None:
    for page in pagination.pages:
        if page.page_number == page_number:
            return page.url
    return None


def _first_cover_image_url(
    page_url: str,
    block: HtmlBlock | None,
    context: HtmlPreviewContext,
) -> str | None:
    if block is not None and block.images:
        image = block.images[0]
    elif context.images:
        image = context.images[0]
    else:
        image = None
    if image is None:
        return None
    return urljoin(page_url, image.src)


def _is_valid_resource_group_label(value: str, link_texts: set[str]) -> bool:
    normalized = _normalize_text(value)
    if not normalized:
        return False
    lowered = normalized.lower()
    if lowered in GENERIC_RESOURCE_GROUP_LABELS or lowered in link_texts:
        return False
    if len(normalized) > RESOURCE_GROUP_LABEL_MAX_LENGTH:
        return False
    if DATE_LIKE_RE.match(normalized) is not None:
        return False
    if FILE_SIZE_LIKE_RE.match(normalized) is not None:
        return False
    if FILE_NAME_LIKE_RE.match(normalized) is not None:
        return False
    return any(keyword in lowered for keyword in RESOURCE_GROUP_KEYWORDS)


def _resource_group_for_hash(block: HtmlBlock | None, info_hash: str) -> str | None:
    if block is None:
        return None
    block_text = _normalize_text(" ".join(block.text_parts))
    link_texts = {_normalize_text(link.text).lower() for link in block.links if link.text}
    target_start = block_text.lower().find(info_hash)
    if target_start < 0:
        return None
    candidates = [
        _normalize_text(candidate)
        for candidate in INFO_HASH_RE.split(block_text[:target_start])
        if _normalize_text(candidate)
    ]
    for candidate in reversed(candidates):
        tail = candidate[-RESOURCE_GROUP_HASH_WINDOW:]
        tail_parts = re.split(r"[。！？；;:：\s]+", tail)
        for part in reversed(tail_parts):
            normalized_part = _normalize_text(part)
            if _is_valid_resource_group_label(normalized_part, link_texts):
                return normalized_part
    return None


def _build_page_preview_items(
    *,
    page_url: str,
    page_number: int,
    html: str,
    existing_hashes: set[str],
    prefer_page_title: bool = False,
) -> tuple[list[str], list[SourcePreviewItem], HtmlPreviewContext]:
    info_hashes = find_info_hashes(html)
    context = _extract_preview_context(html)
    previews: list[SourcePreviewItem] = []
    new_hashes: list[str] = []

    for index, info_hash in enumerate(info_hashes, start=1):
        if info_hash in existing_hashes:
            continue
        existing_hashes.add(info_hash)
        new_hashes.append(info_hash)
        block = _find_block_for_hash(context.blocks, info_hash)
        link = None
        published_at = context.published_at
        if block is not None:
            link = _find_link_for_hash(block.links, info_hash)
            if link is None and not prefer_page_title:
                link = _first_title_link(block.links)
            published_at = block.published_at or context.published_at
        if link is None:
            link = _find_link_for_hash(context.links, info_hash)
        cover_image_url = _first_cover_image_url(page_url, block, context)
        resource_group = _resource_group_for_hash(block, info_hash)
        if prefer_page_title and context.page_title:
            title = context.page_title
        elif link and link.text:
            title = link.text
        elif context.page_title:
            title = context.page_title
        elif block is not None and block.text:
            title = block.text
        else:
            title = f"资源指纹 {index}"
        item_url = (
            page_url
            if prefer_page_title
            else urljoin(page_url, link.href)
            if link and link.href
            else page_url
        )
        previews.append(
            SourcePreviewItem(
                title=title,
                url=item_url,
                info_hash=info_hash,
                magnet_uri=build_magnet_uri(info_hash),
                published_at=published_at,
                resource_group=resource_group,
                cover_image_url=cover_image_url,
                page_number=page_number,
                page_url=page_url,
            )
        )

    return new_hashes, previews, context


def preview_source_items(
    source: SourceSite,
    html: str,
    page_number: int = 1,
    page_url: str | None = None,
    pagination: SourcePagination | None = None,
) -> tuple[int, list[SourcePreviewItem], str | None, SourcePagination]:
    seen_hashes: set[str] = set()
    resolved_page_url = page_url or source.url
    found_hashes, previews, context = _build_page_preview_items(
        page_url=resolved_page_url,
        page_number=page_number,
        html=html,
        existing_hashes=seen_hashes,
    )
    resolved_pagination = pagination or _build_pagination(
        source=source,
        context=context,
        current_page=page_number,
    )
    return (
        len(found_hashes),
        previews[:PREVIEW_ITEM_LIMIT],
        _build_warning_message(source, [context]),
        resolved_pagination,
    )


def _normalize_detail_url(base_url: str, href: str | None) -> str | None:
    if href is None or href.strip() == "":
        return None
    resolved, _fragment = urldefrag(urljoin(base_url, href.strip()))
    parsed = urlparse(resolved)
    base = urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc != base.netloc:
        return None
    if resolved.rstrip("/") == base_url.rstrip("/"):
        return None
    detail_path = parsed.path.rstrip("/")
    base_path = base.path.rstrip("/")
    if detail_path and base_path.startswith(f"{detail_path}/"):
        return None
    return resolved


def _is_likely_listing_url(detail_url: str) -> bool:
    parsed = urlparse(detail_url)
    path_segments = {
        unquote(segment).strip().lower()
        for segment in parsed.path.split("/")
        if segment.strip()
    }
    query_keys = {key.strip().lower() for key, _value in parse_qsl(parsed.query)}
    return bool(path_segments & LISTING_PATH_SEGMENTS or query_keys & PAGINATION_QUERY_KEYS)


def _archive_category_label(context: HtmlPreviewContext) -> str | None:
    match = ARCHIVE_CATEGORY_RE.search(context.visible_text)
    if match is None:
        return None
    return _normalize_text(match.group(1))


def _archive_category_slug(source: SourceSite) -> str | None:
    path_segments = [segment for segment in urlparse(source.url).path.split("/") if segment]
    if not path_segments:
        return None
    slug = path_segments[-1].removesuffix(".html")
    if slug.isdigit() and len(path_segments) >= 2:
        slug = path_segments[-2].removesuffix(".html")
    return slug or None


def _block_is_published_in_category(
    block: HtmlBlock,
    category_label: str | None,
    category_slug: str | None,
) -> bool:
    if (
        category_slug is not None
        and block.tag_name == "article"
        and f"category-{category_slug}" in block.classes
    ):
        return True
    if category_label is None or "发表在" not in block.text:
        return False
    return any(_normalize_text(link.text) == category_label for link in block.links)


def _append_detail_candidate(
    *,
    base_url: str,
    link: HtmlLink,
    seen: set[str],
    result: list[DetailPageCandidate],
) -> None:
    detail_url = _normalize_detail_url(base_url, link.href)
    if detail_url is None or detail_url in seen or _is_likely_listing_url(detail_url):
        return
    seen.add(detail_url)
    result.append(
        DetailPageCandidate(
            url=detail_url,
            title=_normalize_text(link.text) or None,
        )
    )


def _detail_candidates_from_context(
    source: SourceSite,
    context: HtmlPreviewContext,
) -> list[DetailPageCandidate]:
    settings = get_settings()
    seen: set[str] = set()
    result: list[DetailPageCandidate] = []

    content_blocks = [
        block
        for block in context.blocks
        if len(block.text) >= ARTICLE_BLOCK_MIN_TEXT_LENGTH and block.links
    ]
    archive_category = _archive_category_label(context)
    archive_slug = _archive_category_slug(source)
    if archive_category is not None or archive_slug is not None:
        content_blocks = [
            block
            for block in content_blocks
            if _block_is_published_in_category(block, archive_category, archive_slug)
        ]
    for block in content_blocks:
        link = _first_title_link(block.links)
        if link is None:
            continue
        _append_detail_candidate(
            base_url=source.url,
            link=link,
            seen=seen,
            result=result,
        )
        if len(result) >= settings.source_detail_scan_max_pages:
            break

    if not result and archive_category is None:
        for link in (link for link in context.links if link.text.strip()):
            _append_detail_candidate(
                base_url=source.url,
                link=link,
                seen=seen,
                result=result,
            )
            if len(result) >= settings.source_detail_scan_max_pages:
                break
    return result


def _detail_urls_from_context(source: SourceSite, context: HtmlPreviewContext) -> list[str]:
    return [candidate.url for candidate in _detail_candidates_from_context(source, context)]


def preview_source_items_with_detail_pages(
    source: SourceSite,
    list_html: str,
    page_number: int = 1,
    page_url: str | None = None,
    pagination: SourcePagination | None = None,
) -> tuple[
    int,
    list[SourcePreviewItem],
    str | None,
    SourcePagination,
    list[SourceScanFailure],
]:
    seen_hashes: set[str] = set()
    resolved_page_url = page_url or source.url
    found_hashes, previews, list_context = _build_page_preview_items(
        page_url=resolved_page_url,
        page_number=page_number,
        html=list_html,
        existing_hashes=seen_hashes,
    )
    contexts = [list_context]
    resolved_pagination = pagination or _build_pagination(
        source=source,
        context=list_context,
        current_page=page_number,
    )
    failures: list[SourceScanFailure] = []

    for candidate in _detail_candidates_from_context(source, list_context):
        try:
            response = _fetch_source_url(candidate.url)
        except httpx.HTTPError:
            failures.append(
                SourceScanFailure(
                    url=candidate.url,
                    title=candidate.title,
                    message=DETAIL_PAGE_FETCH_FAILED,
                )
            )
            continue
        detail_hashes, detail_previews, detail_context = _build_page_preview_items(
            page_url=candidate.url,
            page_number=page_number,
            html=response.text,
            existing_hashes=seen_hashes,
            prefer_page_title=True,
        )
        found_hashes.extend(detail_hashes)
        previews.extend(detail_previews)
        contexts.append(detail_context)

    return (
        len(found_hashes),
        previews[:PREVIEW_ITEM_LIMIT],
        _build_warning_message(source, contexts),
        resolved_pagination,
        failures,
    )


def test_source(
    db: Session,
    source: SourceSite,
    page_number: int = 1,
) -> tuple[
    int,
    list[SourcePreviewItem],
    str | None,
    SourcePagination,
    list[SourceScanFailure],
]:
    try:
        response = _fetch_source_url(source.url, attempts=SOURCE_FETCH_ATTEMPTS)
    except httpx.HTTPError as exc:
        raise SourceTestError(SOURCE_TEST_ERROR) from exc

    first_context = _extract_preview_context(response.text)
    pagination = _build_pagination(source=source, context=first_context, current_page=page_number)
    page_url = source.url
    page_html = response.text
    if page_number > 1:
        selected_page_url = _pagination_url_for_page(pagination, page_number)
        if selected_page_url is None:
            raise SourceTestError("未找到指定页码，请先确认来源分页是否可识别")
        try:
            selected_response = _fetch_source_url(selected_page_url, attempts=SOURCE_FETCH_ATTEMPTS)
        except httpx.HTTPError as exc:
            raise SourceTestError(SOURCE_TEST_ERROR) from exc
        page_url = selected_page_url
        page_html = selected_response.text

    source.last_checked_at = datetime.utcnow()
    db.add(source)
    db.commit()
    if source.scan_detail_pages:
        return preview_source_items_with_detail_pages(
            source,
            page_html,
            page_number=page_number,
            page_url=page_url,
            pagination=pagination,
        )
    found_count, items, warning_message, resolved_pagination = preview_source_items(
        source,
        page_html,
        page_number=page_number,
        page_url=page_url,
        pagination=pagination,
    )
    return found_count, items, warning_message, resolved_pagination, []

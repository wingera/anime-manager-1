from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import SourceItem, SourceSite
from app.schemas.sources import SourcePreviewItem, SourceSiteCreate, SourceSiteUpdate
from app.utils.info_hash import build_magnet_uri, find_info_hashes, normalize_info_hash

SOURCE_TEST_ERROR = "来源测试失败，请检查地址是否可访问"
AUTH_NOTE_REQUIRED_ERROR = "启用来源前必须填写授权备注"


class SourceTestError(RuntimeError):
    pass


@dataclass(frozen=True)
class HtmlLink:
    text: str
    href: str | None


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[HtmlLink] = []
        self._active_href: str | None = None
        self._active_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._active_href = next((value for key, value in attrs if key.lower() == "href"), None)
        self._active_text = []

    def handle_data(self, data: str) -> None:
        if self._active_href is not None:
            self._active_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._active_href is None:
            return
        title = " ".join("".join(self._active_text).split())
        self.links.append(HtmlLink(text=title, href=self._active_href))
        self._active_href = None
        self._active_text = []


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
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_source_items(db: Session) -> list[SourceItem]:
    return list(
        db.scalars(select(SourceItem).order_by(SourceItem.created_at.desc(), SourceItem.id.desc()))
    )


def _extract_links(html: str) -> list[HtmlLink]:
    parser = _LinkParser()
    parser.feed(html)
    return parser.links


def _find_link_for_hash(links: list[HtmlLink], info_hash: str) -> HtmlLink | None:
    for link in links:
        hash_in_text = info_hash in link.text.lower()
        hash_in_href = link.href is not None and info_hash in link.href.lower()
        if hash_in_text or hash_in_href:
            return link
    return None


def preview_source_items(source: SourceSite, html: str) -> tuple[int, list[SourcePreviewItem]]:
    info_hashes = find_info_hashes(html)
    links = _extract_links(html)
    previews: list[SourcePreviewItem] = []

    for index, info_hash in enumerate(info_hashes[:20], start=1):
        link = _find_link_for_hash(links, info_hash)
        title = link.text if link and link.text else f"资源指纹 {index}"
        item_url = urljoin(source.url, link.href) if link and link.href else None
        previews.append(
            SourcePreviewItem(
                title=title,
                url=item_url,
                info_hash=info_hash,
                magnet_uri=build_magnet_uri(info_hash),
            )
        )

    return len(info_hashes), previews


def test_source(db: Session, source: SourceSite) -> tuple[int, list[SourcePreviewItem]]:
    try:
        response = httpx.get(source.url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SourceTestError(SOURCE_TEST_ERROR) from exc

    source.last_checked_at = datetime.utcnow()
    db.add(source)
    db.commit()
    return preview_source_items(source, response.text)

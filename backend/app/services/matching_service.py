import re
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MediaMatch, SourceItem
from app.integrations.tmdb import TmdbSearchError, search_tv
from app.schemas.matching import MediaMatchSaveRequest, TmdbCandidate
from app.services.settings_service import get_or_create_settings
from app.utils.secrets import decrypt_secret
from app.utils.title_parser import clean_search_title, guess_season_episode, guess_year

TMDB_API_KEY_REQUIRED_ERROR = "请先填写 TMDB API 密钥"
TMDB_QUERY_LIMIT = 5
LEADING_BRACKET_GROUP_RE = re.compile(r"^\s*[\[【(（][^\]】)）]{1,40}[\]】)）]\s*")
RESOURCE_HINT_RE = re.compile(r"(资源指纹|磁力入口|磁力|magnet|btih)", re.IGNORECASE)
EPISODE_SUFFIX_RE = re.compile(
    r"\s*(第\s*\d+\s*[巻卷话話集]|[＃#]\s*\d+|vol\.?\s*\d+).*$",
    re.IGNORECASE,
)
ANIMATION_SUFFIX_RE = re.compile(r"\s+the\s+animation$", re.IGNORECASE)
OVA_MARKER_RE = re.compile(r"(?<![a-z0-9])ova(?![a-z0-9])", re.IGNORECASE)


def get_source_item(db: Session, item_id: int) -> SourceItem | None:
    return db.get(SourceItem, item_id)


def _title_similarity(source_title: str, candidate_title: str, original_title: str | None) -> float:
    source = source_title.lower()
    titles = [candidate_title.lower()]
    if original_title:
        titles.append(original_title.lower())
    return max(SequenceMatcher(None, source, title).ratio() for title in titles)


def _candidate_year(first_air_date: str | None) -> int | None:
    if not first_air_date or len(first_air_date) < 4:
        return None
    try:
        return int(first_air_date[:4])
    except ValueError:
        return None


def _score_candidate(
    *,
    source_title: str,
    source_year: int | None,
    season_number: int | None,
    episode_number: int | None,
    candidate_title: str,
    original_title: str | None,
    first_air_date: str | None,
) -> float:
    score = _title_similarity(source_title, candidate_title, original_title) * 40
    candidate_year = _candidate_year(first_air_date)
    if source_year is not None and candidate_year is not None:
        score += max(0, 15 - min(abs(source_year - candidate_year), 15))
    if season_number is not None or episode_number is not None:
        score += 30
    score += 5
    return round(min(score, 100), 2)


def _normalize_query_text(value: str) -> str:
    cleaned = RESOURCE_HINT_RE.sub(" ", value)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" /-_:：，,|")


def _add_query(result: list[str], value: str) -> None:
    query = _normalize_query_text(value)
    if len(query) < 2:
        return
    normalized_existing = {item.casefold() for item in result}
    if query.casefold() not in normalized_existing:
        result.append(query)


def _without_ova_marker(value: str) -> str:
    return _normalize_query_text(OVA_MARKER_RE.sub(" ", value))


def build_tmdb_search_queries(title: str) -> list[str]:
    without_group = LEADING_BRACKET_GROUP_RE.sub("", title)
    cleaned_without_group = clean_search_title(without_group)
    cleaned_full = clean_search_title(title)
    queries: list[str] = []

    base = EPISODE_SUFFIX_RE.sub("", cleaned_without_group).strip()
    short_base = ANIMATION_SUFFIX_RE.sub("", base).strip()
    _add_query(queries, short_base)
    _add_query(queries, _without_ova_marker(short_base))
    _add_query(queries, base)
    _add_query(queries, _without_ova_marker(base))
    _add_query(queries, EPISODE_SUFFIX_RE.sub("", cleaned_full))
    _add_query(queries, cleaned_without_group)
    _add_query(queries, cleaned_full)

    return queries[:TMDB_QUERY_LIMIT]


def search_tmdb_candidates(db: Session, item: SourceItem) -> tuple[list[str], list[TmdbCandidate]]:
    settings = get_or_create_settings(db)
    api_key = decrypt_secret(settings.tmdb_api_key)
    if not api_key:
        raise ValueError(TMDB_API_KEY_REQUIRED_ERROR)

    search_queries = build_tmdb_search_queries(item.title)
    if not search_queries:
        search_queries = [item.title.strip()]
    source_year = guess_year(item.title)
    season_number, episode_number = guess_season_episode(item.title)
    candidates_by_id: dict[int, TmdbCandidate] = {}

    for search_query in search_queries:
        results = search_tv(
            api_key=api_key,
            language=settings.tmdb_language,
            region=settings.tmdb_region,
            query=search_query,
            include_adult=settings.tmdb_include_adult,
        )
        for result in results[:10]:
            candidate = TmdbCandidate(
                tmdb_id=result.tmdb_id,
                title=result.title,
                original_title=result.original_title,
                first_air_date=result.first_air_date,
                overview=result.overview,
                poster_path=result.poster_path,
                match_score=_score_candidate(
                    source_title=search_query,
                    source_year=source_year,
                    season_number=season_number,
                    episode_number=episode_number,
                    candidate_title=result.title,
                    original_title=result.original_title,
                    first_air_date=result.first_air_date,
                ),
                search_query=search_query,
            )
            existing = candidates_by_id.get(candidate.tmdb_id)
            if existing is None or candidate.match_score > existing.match_score:
                candidates_by_id[candidate.tmdb_id] = candidate

    candidates = sorted(
        candidates_by_id.values(),
        key=lambda candidate: candidate.match_score,
        reverse=True,
    )
    return search_queries, candidates[:10]


def save_media_match(
    db: Session,
    *,
    source_item_id: int,
    payload: MediaMatchSaveRequest,
) -> MediaMatch:
    media_match = db.scalar(
        select(MediaMatch).where(MediaMatch.source_item_id == source_item_id)
    )
    if media_match is None:
        media_match = MediaMatch(source_item_id=source_item_id)

    data = payload.model_dump()
    for field, value in data.items():
        setattr(media_match, field, value.strip() if isinstance(value, str) else value)

    db.add(media_match)
    db.commit()
    db.refresh(media_match)
    return media_match


def list_media_matches(db: Session) -> list[MediaMatch]:
    return list(
        db.scalars(select(MediaMatch).order_by(MediaMatch.created_at.desc(), MediaMatch.id.desc()))
    )


__all__ = ["TmdbSearchError"]

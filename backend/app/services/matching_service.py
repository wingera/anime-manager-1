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


def search_tmdb_candidates(db: Session, item: SourceItem) -> list[TmdbCandidate]:
    settings = get_or_create_settings(db)
    api_key = decrypt_secret(settings.tmdb_api_key)
    if not api_key:
        raise ValueError(TMDB_API_KEY_REQUIRED_ERROR)

    search_title = clean_search_title(item.title) or item.title
    source_year = guess_year(item.title)
    season_number, episode_number = guess_season_episode(item.title)

    results = search_tv(
        api_key=api_key,
        language=settings.tmdb_language,
        region=settings.tmdb_region,
        query=search_title,
    )
    return [
        TmdbCandidate(
            tmdb_id=result.tmdb_id,
            title=result.title,
            original_title=result.original_title,
            first_air_date=result.first_air_date,
            overview=result.overview,
            poster_path=result.poster_path,
            match_score=_score_candidate(
                source_title=search_title,
                source_year=source_year,
                season_number=season_number,
                episode_number=episode_number,
                candidate_title=result.title,
                original_title=result.original_title,
                first_air_date=result.first_air_date,
            ),
        )
        for result in results[:10]
    ]


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

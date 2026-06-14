from dataclasses import dataclass
from typing import Any

import httpx

from app.schemas.settings import ConnectionTestResponse

TMDB_SEARCH_ERROR = "TMDB 搜索失败，请检查网络或 API 密钥"


class TmdbSearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class TmdbTvResult:
    tmdb_id: int
    title: str
    original_title: str | None
    first_air_date: str | None
    overview: str
    poster_path: str | None


def test_tmdb_connection(api_key: str | None, language: str) -> ConnectionTestResponse:
    if not api_key:
        return ConnectionTestResponse(success=False, message="请先填写 TMDB API 密钥")

    try:
        response = httpx.get(
            "https://api.themoviedb.org/3/configuration",
            params={"api_key": api_key, "language": language},
            timeout=10.0,
        )
    except httpx.RequestError:
        return ConnectionTestResponse(success=False, message="TMDB 连接失败：网络异常")

    if response.status_code == 200:
        return ConnectionTestResponse(success=True, message="TMDB 连接成功")

    return ConnectionTestResponse(success=False, message="TMDB 连接失败，请检查 API 密钥")


def search_tv(api_key: str, language: str, region: str, query: str) -> list[TmdbTvResult]:
    try:
        response = httpx.get(
            "https://api.themoviedb.org/3/search/tv",
            params={
                "api_key": api_key,
                "language": language,
                "region": region,
                "query": query,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        payload: Any = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise TmdbSearchError(TMDB_SEARCH_ERROR) from exc

    results = payload.get("results", []) if isinstance(payload, dict) else []
    candidates: list[TmdbTvResult] = []
    for item in results[:10]:
        if not isinstance(item, dict):
            continue
        tmdb_id = item.get("id")
        title = item.get("name")
        if not isinstance(tmdb_id, int) or not isinstance(title, str):
            continue
        original_title = item.get("original_name")
        first_air_date = item.get("first_air_date")
        overview = item.get("overview")
        poster_path = item.get("poster_path")
        candidates.append(
            TmdbTvResult(
                tmdb_id=tmdb_id,
                title=title,
                original_title=original_title if isinstance(original_title, str) else None,
                first_air_date=first_air_date if isinstance(first_air_date, str) else None,
                overview=overview if isinstance(overview, str) else "",
                poster_path=poster_path if isinstance(poster_path, str) else None,
            )
        )
    return candidates

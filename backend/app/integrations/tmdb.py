import httpx

from app.schemas.settings import ConnectionTestResponse


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

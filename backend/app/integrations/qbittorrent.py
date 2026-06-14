from urllib.parse import urljoin

import httpx

from app.schemas.settings import ConnectionTestResponse


def test_qbittorrent_connection(
    url: str | None,
    username: str | None,
    password: str | None,
) -> ConnectionTestResponse:
    if not url or not username or not password:
        return ConnectionTestResponse(
            success=False,
            message="请先填写 qBittorrent 地址、用户名和密码",
        )

    login_url = urljoin(url.rstrip("/") + "/", "api/v2/auth/login")
    try:
        response = httpx.post(
            login_url,
            data={"username": username, "password": password},
            timeout=10.0,
        )
    except httpx.RequestError:
        return ConnectionTestResponse(success=False, message="qBittorrent 连接失败：网络异常")

    if response.status_code == 200 and response.text.strip().lower() == "ok.":
        return ConnectionTestResponse(success=True, message="qBittorrent 连接成功")

    return ConnectionTestResponse(
        success=False,
        message="qBittorrent 连接失败，请检查地址、用户名和密码",
    )

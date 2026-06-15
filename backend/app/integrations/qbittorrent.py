from urllib.parse import urljoin

import httpx

from app.schemas.settings import ConnectionTestResponse

QB_NOT_CONFIGURED_MESSAGE = "请先填写 qBittorrent 地址、用户名和密码"
QB_REQUEST_FAILED_MESSAGE = "qBittorrent 请求失败，请检查连接设置"


def _require_config(
    url: str | None,
    username: str | None,
    password: str | None,
) -> tuple[str, str, str]:
    if not url or not username or not password:
        raise ValueError(QB_NOT_CONFIGURED_MESSAGE)
    return url, username, password


def _api_url(url: str, path: str) -> str:
    return urljoin(url.rstrip("/") + "/", path)


def _extract_hash_from_magnet(magnet_uri: str) -> str:
    marker = "btih:"
    marker_index = magnet_uri.lower().find(marker)
    if marker_index == -1:
        return ""
    candidate = magnet_uri[marker_index + len(marker) :].split("&", 1)[0].lower()
    if len(candidate) == 40 and all(char in "0123456789abcdef" for char in candidate):
        return candidate
    return ""


def _is_login_success(response: httpx.Response) -> bool:
    if response.status_code == 200 and response.text.strip().lower() == "ok.":
        return True
    if response.status_code == 204 and any(
        key.upper().startswith("QBT_SID") for key in response.cookies.keys()
    ):
        return True
    return False


def _login(client: httpx.Client, url: str, username: str, password: str) -> None:
    response = client.post(
        _api_url(url, "api/v2/auth/login"),
        data={"username": username, "password": password},
    )
    if not _is_login_success(response):
        raise ValueError("qBittorrent 认证失败，请检查地址、用户名和密码")


def test_qbittorrent_connection(
    url: str | None,
    username: str | None,
    password: str | None,
) -> ConnectionTestResponse:
    if not url or not username or not password:
        return ConnectionTestResponse(
            success=False,
            message=QB_NOT_CONFIGURED_MESSAGE,
        )

    login_url = _api_url(url, "api/v2/auth/login")
    try:
        response = httpx.post(
            login_url,
            data={"username": username, "password": password},
            timeout=10.0,
        )
    except httpx.RequestError:
        return ConnectionTestResponse(success=False, message="qBittorrent 连接失败：网络异常")

    if _is_login_success(response):
        return ConnectionTestResponse(success=True, message="qBittorrent 连接成功")

    return ConnectionTestResponse(
        success=False,
        message="qBittorrent 连接失败，请检查地址、用户名和密码",
    )


def add_paused_magnet(
    url: str | None,
    username: str | None,
    password: str | None,
    magnet_uri: str,
    save_path: str,
) -> str:
    configured_url, configured_username, configured_password = _require_config(
        url,
        username,
        password,
    )
    try:
        with httpx.Client(timeout=10.0) as client:
            _login(client, configured_url, configured_username, configured_password)
            response = client.post(
                _api_url(configured_url, "api/v2/torrents/add"),
                data={
                    "urls": magnet_uri,
                    "savepath": save_path,
                    "paused": "true",
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ValueError(QB_REQUEST_FAILED_MESSAGE) from exc

    return _extract_hash_from_magnet(magnet_uri)


def get_torrent_status(
    url: str | None,
    username: str | None,
    password: str | None,
    torrent_hash: str,
) -> dict[str, object]:
    configured_url, configured_username, configured_password = _require_config(
        url,
        username,
        password,
    )
    try:
        with httpx.Client(timeout=10.0) as client:
            _login(client, configured_url, configured_username, configured_password)
            response = client.get(
                _api_url(configured_url, "api/v2/torrents/info"),
                params={"hashes": torrent_hash},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ValueError(QB_REQUEST_FAILED_MESSAGE) from exc

    data = response.json()
    if not isinstance(data, list) or not data:
        return {"status": "missing", "progress": 0.0, "error_message": "下载器中未找到该任务"}

    torrent = data[0]
    if not isinstance(torrent, dict):
        return {"status": "unknown", "progress": 0.0, "error_message": "下载器返回状态无法识别"}

    progress = torrent.get("progress", 0.0)
    state = torrent.get("state", "unknown")
    error_message = torrent.get("error_string") or None
    return {
        "status": str(state),
        "progress": float(progress) if isinstance(progress, int | float) else 0.0,
        "error_message": str(error_message) if error_message else None,
    }


def get_torrent_files(
    url: str | None,
    username: str | None,
    password: str | None,
    torrent_hash: str,
) -> list[dict[str, object]]:
    configured_url, configured_username, configured_password = _require_config(
        url,
        username,
        password,
    )
    try:
        with httpx.Client(timeout=10.0) as client:
            _login(client, configured_url, configured_username, configured_password)
            response = client.get(
                _api_url(configured_url, "api/v2/torrents/files"),
                params={"hash": torrent_hash},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ValueError(QB_REQUEST_FAILED_MESSAGE) from exc

    data = response.json()
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def set_file_priority(
    url: str | None,
    username: str | None,
    password: str | None,
    torrent_hash: str,
    file_indexes: list[int],
    priority: int,
) -> None:
    if not file_indexes:
        return
    configured_url, configured_username, configured_password = _require_config(
        url,
        username,
        password,
    )
    try:
        with httpx.Client(timeout=10.0) as client:
            _login(client, configured_url, configured_username, configured_password)
            response = client.post(
                _api_url(configured_url, "api/v2/torrents/filePrio"),
                data={
                    "hash": torrent_hash,
                    "id": "|".join(str(index) for index in file_indexes),
                    "priority": str(priority),
                },
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ValueError(QB_REQUEST_FAILED_MESSAGE) from exc

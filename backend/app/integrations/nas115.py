from typing import Any
from urllib.parse import urljoin

import httpx

from app.schemas.settings import ConnectionTestResponse

NAS115_NOT_CONFIGURED_MESSAGE = "请先填写 NAS 115 服务地址"
NAS115_REQUEST_FAILED_MESSAGE = "NAS 115 服务请求失败，请检查服务地址和令牌"
NAS115_CAPABILITY_MISSING_MESSAGE = "115 服务未提供该能力，请检查 NAS 服务接口。"
DEFAULT_TIMEOUT = 10.0
QueryValue = str | int | float | bool | None


def _require_url(service_url: str | None) -> str:
    if not service_url or not service_url.strip():
        raise ValueError(NAS115_NOT_CONFIGURED_MESSAGE)
    return service_url.strip()


def _api_url(service_url: str, path: str) -> str:
    return urljoin(service_url.rstrip("/") + "/", path.lstrip("/"))


def _headers(token: str | None) -> dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _json_response(response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError("NAS 115 服务返回内容无法识别") from exc
    if not isinstance(data, dict):
        raise ValueError("NAS 115 服务返回内容无法识别")
    return data


def _request(
    method: str,
    service_url: str | None,
    token: str | None,
    path: str,
    *,
    params: dict[str, QueryValue] | None = None,
    json: dict[str, object] | None = None,
) -> dict[str, Any]:
    configured_url = _require_url(service_url)
    try:
        response = httpx.request(
            method,
            _api_url(configured_url, path),
            headers=_headers(token),
            params=params,
            json=json,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            raise ValueError("NAS 115 服务认证失败，请检查服务令牌") from exc
        raise ValueError(NAS115_REQUEST_FAILED_MESSAGE) from exc
    except httpx.TimeoutException as exc:
        raise ValueError("NAS 115 服务连接超时，请检查 NAS 服务状态") from exc
    except httpx.RequestError as exc:
        raise ValueError("NAS 115 服务连接失败，请检查服务地址") from exc
    return _json_response(response)


def test_nas115_connection(service_url: str | None, token: str | None) -> ConnectionTestResponse:
    if not service_url or not service_url.strip():
        return ConnectionTestResponse(success=False, message=NAS115_NOT_CONFIGURED_MESSAGE)
    try:
        data = _request(
            "POST",
            service_url,
            token,
            "/api/config/check_domain",
            json={"url": service_url},
        )
    except ValueError as exc:
        return ConnectionTestResponse(success=False, message=str(exc))
    if data.get("code") == 200:
        return ConnectionTestResponse(success=True, message="NAS 115 服务连接成功")
    return ConnectionTestResponse(
        success=False,
        message=str(data.get("msg") or "NAS 115 服务连接失败"),
    )


def add_magnet_task(service_url: str | None, token: str | None, magnet_uri: str) -> str:
    data = _request(
        "POST",
        service_url,
        token,
        "/api/cloud/add_share_down",
        json={"url": magnet_uri},
    )
    if data.get("code") != 200:
        raise ValueError(str(data.get("msg") or "NAS 115 磁力任务提交失败"))
    payload = data.get("data")
    if isinstance(payload, dict):
        task_id = payload.get("id") or payload.get("task_id") or payload.get("async_task_id")
        if task_id is not None:
            return str(task_id)
    task_id = data.get("id") or data.get("task_id") or data.get("async_task_id")
    if task_id is not None:
        return str(task_id)
    return ""


def get_task_status(service_url: str | None, token: str | None, task_id: str) -> dict[str, object]:
    record = _find_share_down_record(service_url, token, task_id)
    if record is None:
        return {"status": "missing", "progress": 0.0, "error_message": "NAS 115 服务中未找到该任务"}
    status = _status_label(record.get("status"))
    return {
        "status": status,
        "progress": 1.0 if status == "completed" else 0.0,
        "error_message": str(record.get("remark")) if record.get("remark") else None,
    }


def list_task_files(
    service_url: str | None,
    token: str | None,
    task_id: str,
) -> list[dict[str, object]]:
    record = _find_share_down_record(service_url, token, task_id)
    if record is None:
        raise ValueError("NAS 115 服务中未找到该任务")
    file_id = record.get("f_id")
    file_name = record.get("f_name") or record.get("share_name")
    if file_id and file_name:
        return [
            {
                "id": str(file_id),
                "name": str(file_name),
                "parent_id": None,
                "size": 0,
                "progress": 1.0 if _status_label(record.get("status")) == "completed" else 0.0,
            }
        ]
    raise ValueError(NAS115_CAPABILITY_MISSING_MESSAGE)


def rename_file(service_url: str | None, token: str | None, file_id: str, new_name: str) -> None:
    raise ValueError(NAS115_CAPABILITY_MISSING_MESSAGE)


def move_file(
    service_url: str | None,
    token: str | None,
    file_id: str,
    target_parent_id: str,
) -> None:
    raise ValueError(NAS115_CAPABILITY_MISSING_MESSAGE)


def create_folder(
    service_url: str | None,
    token: str | None,
    parent_id: str | None,
    folder_name: str,
) -> str:
    raise ValueError(NAS115_CAPABILITY_MISSING_MESSAGE)


def check_name_exists(
    service_url: str | None,
    token: str | None,
    parent_id: str | None,
    name: str,
) -> bool:
    raise ValueError(NAS115_CAPABILITY_MISSING_MESSAGE)


def _find_share_down_record(
    service_url: str | None,
    token: str | None,
    task_id: str,
) -> dict[str, Any] | None:
    data = _request(
        "GET",
        service_url,
        token,
        "/api/share_down/list",
        params={"page": 1, "page_size": 100, "id": task_id},
    )
    records = data.get("data")
    if not isinstance(records, list):
        return None
    for item in records:
        if isinstance(item, dict) and str(item.get("id")) == str(task_id):
            return item
    return None


def _status_label(value: object) -> str:
    if value in {2, "2", "completed", "success", "done"}:
        return "completed"
    if value in {-1, "failed", "error"}:
        return "failed"
    if value in {1, "1", "running", "pending", "submitted"}:
        return "submitted"
    return "unknown"

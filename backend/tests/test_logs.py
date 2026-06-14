from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.log_service import write_operation_log


def test_logs_returns_empty_list_by_default(client: TestClient) -> None:
    response = client.get("/api/logs")

    assert response.status_code == 200
    assert response.json() == {"message": "运行日志获取成功", "logs": []}


def test_logs_can_query_written_log_by_module(
    client: TestClient,
    db_session: Session,
) -> None:
    write_operation_log(
        db_session,
        level="info",
        module="settings",
        message="系统设置已保存",
        detail="已更新下载目录和媒体库目录",
    )
    write_operation_log(
        db_session,
        level="warning",
        module="downloads",
        message="下载任务创建失败",
        detail="磁力入口参数已脱敏",
    )

    response = client.get("/api/logs", params={"module": "settings"})

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "运行日志获取成功"
    assert len(data["logs"]) == 1
    assert data["logs"][0]["module"] == "settings"
    assert data["logs"][0]["message"] == "系统设置已保存"

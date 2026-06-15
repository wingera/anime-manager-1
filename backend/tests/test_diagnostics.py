from fastapi.testclient import TestClient


def test_diagnostics_returns_checks(client: TestClient) -> None:
    response = client.get("/api/diagnostics")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "系统诊断完成"
    names = {check["name"] for check in data["checks"]}
    assert "数据目录" in names
    assert "数据库连接" in names
    assert "密钥文件" in names


def test_diagnostics_database_check_is_ok(client: TestClient) -> None:
    response = client.get("/api/diagnostics")

    checks = response.json()["checks"]
    database_check = next(check for check in checks if check["name"] == "数据库连接")
    assert database_check["status"] == "ok"
    assert database_check["message"] == "数据库连接正常"

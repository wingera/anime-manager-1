from fastapi.testclient import TestClient


def test_dashboard_summary_returns_counts_and_latest_logs(client: TestClient) -> None:
    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "任务看板获取成功"
    summary = data["summary"]
    for field in [
        "sources_count",
        "source_items_count",
        "matches_count",
        "confirmed_matches_count",
        "downloads_count",
        "download_files_count",
        "rename_previews_count",
        "imports_count",
        "failed_imports_count",
        "latest_logs",
    ]:
        assert field in summary
    assert summary["latest_logs"] == []

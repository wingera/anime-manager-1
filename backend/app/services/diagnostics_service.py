import os
import shutil
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.integrations.nas115 import test_nas115_connection
from app.schemas.diagnostics import DiagnosticCheck, DiagnosticsResponse, DiagnosticStatus
from app.services.settings_service import get_or_create_settings
from app.utils.secrets import decrypt_secret


def _check_writable_directory(name: str, path: Path, *, must_exist: bool) -> DiagnosticCheck:
    if not path.exists():
        status: DiagnosticStatus = "error" if must_exist else "warning"
        return DiagnosticCheck(name=name, status=status, message=f"{name}不存在：{path}")
    if not path.is_dir():
        return DiagnosticCheck(name=name, status="error", message=f"{name}不是目录：{path}")
    if not os.access(path, os.W_OK):
        return DiagnosticCheck(name=name, status="error", message=f"{name}不可写：{path}")
    return DiagnosticCheck(name=name, status="ok", message=f"{name}可写")


def _check_executable(command: str) -> DiagnosticCheck:
    if shutil.which(command):
        return DiagnosticCheck(name=command, status="ok", message=f"{command} 可执行")
    return DiagnosticCheck(
        name=command,
        status="warning",
        message=f"未找到 {command}，视频分析能力受限",
    )


def run_diagnostics(db: Session) -> DiagnosticsResponse:
    app_settings = get_settings()
    settings = get_or_create_settings(db)
    checks: list[DiagnosticCheck] = []

    checks.append(_check_writable_directory("数据目录", app_settings.data_dir, must_exist=False))
    checks.append(
        _check_writable_directory("下载目录", Path(settings.download_dir), must_exist=True)
    )
    checks.append(
        _check_writable_directory("媒体库目录", Path(settings.media_library_dir), must_exist=True)
    )
    checks.append(_check_executable("ffmpeg"))
    checks.append(_check_executable("ffprobe"))

    if settings.qbittorrent_url and settings.qbittorrent_username and settings.qbittorrent_password:
        checks.append(
            DiagnosticCheck(name="qBittorrent 配置", status="ok", message="qBittorrent 已配置")
        )
    else:
        checks.append(
            DiagnosticCheck(
                name="qBittorrent 配置",
                status="warning",
                message="qBittorrent 地址、用户名或密码未完整配置",
            )
        )

    if settings.cloud115_enabled:
        result = test_nas115_connection(
            settings.cloud115_service_url,
            decrypt_secret(settings.cloud115_service_token),
        )
        checks.append(
            DiagnosticCheck(
                name="NAS 115 服务",
                status="ok" if result.success else "warning",
                message=result.message,
            )
        )
    else:
        checks.append(
            DiagnosticCheck(
                name="NAS 115 服务",
                status="warning",
                message="NAS 115 服务未启用",
            )
        )
    checks.append(
        DiagnosticCheck(
            name="NAS 115 重命名接口",
            status="warning",
            message="未发现",
        )
    )

    if settings.tmdb_api_key:
        checks.append(DiagnosticCheck(name="TMDB 配置", status="ok", message="TMDB 已配置"))
    else:
        checks.append(
            DiagnosticCheck(name="TMDB 配置", status="warning", message="TMDB API 密钥未配置")
        )

    try:
        db.execute(text("select 1"))
    except Exception:
        checks.append(
            DiagnosticCheck(name="数据库连接", status="error", message="数据库连接失败，请检查配置")
        )
    else:
        checks.append(DiagnosticCheck(name="数据库连接", status="ok", message="数据库连接正常"))

    secret_file = app_settings.data_dir / "secret.key"
    if os.getenv("SECRET_KEY") or secret_file.exists():
        checks.append(DiagnosticCheck(name="密钥文件", status="ok", message="密钥已配置"))
    else:
        checks.append(
            DiagnosticCheck(
                name="密钥文件",
                status="warning",
                message="未发现 SECRET_KEY 或 data/secret.key",
            )
        )

    checks.append(
        DiagnosticCheck(
            name="Docker 挂载目录",
            status="warning",
            message="请确认 data、下载目录和媒体库目录已通过 Docker 挂载持久化",
        )
    )

    return DiagnosticsResponse(message="系统诊断完成", checks=checks)

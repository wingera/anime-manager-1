from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppSettings, DownloadTask, MediaMatch, SourceItem
from app.integrations.nas115 import (
    add_magnet_task as add_nas115_magnet_task,
)
from app.integrations.nas115 import (
    get_task_status as get_nas115_task_status,
)
from app.integrations.qbittorrent import add_paused_magnet, get_torrent_status
from app.schemas.downloads import DownloadTaskResponse
from app.services.settings_service import get_or_create_settings
from app.utils.secrets import decrypt_secret

MATCH_REQUIRED_MESSAGE = "请先确认资料匹配后再创建下载任务"
QB_NOT_CONFIGURED_MESSAGE = "请先填写 qBittorrent 地址、用户名和密码"
HASH_PENDING_MESSAGE = "下载器尚未返回任务哈希，请稍后刷新"
NAS115_NOT_CONFIGURED_MESSAGE = "请先启用并填写 NAS 115 服务地址"


def _settings_credentials(settings: AppSettings) -> tuple[str, str, str]:
    password = decrypt_secret(settings.qbittorrent_password)
    if not settings.qbittorrent_url or not settings.qbittorrent_username or not password:
        raise ValueError(QB_NOT_CONFIGURED_MESSAGE)
    return settings.qbittorrent_url, settings.qbittorrent_username, password


def _nas115_credentials(settings: AppSettings) -> tuple[str, str | None]:
    if not settings.cloud115_enabled or not settings.cloud115_service_url:
        raise ValueError(NAS115_NOT_CONFIGURED_MESSAGE)
    return settings.cloud115_service_url, decrypt_secret(settings.cloud115_service_token)


def _to_response(download: DownloadTask, source_item: SourceItem) -> DownloadTaskResponse:
    return DownloadTaskResponse(
        id=download.id,
        source_item_id=download.source_item_id,
        source_title=source_item.title,
        qbittorrent_hash=download.qbittorrent_hash,
        provider=download.provider,
        provider_task_id=download.provider_task_id,
        magnet_uri=download.magnet_uri,
        save_path=download.save_path,
        status=download.status,
        progress=download.progress,
        error_message=download.error_message,
        created_at=download.created_at,
        updated_at=download.updated_at,
    )


def list_download_tasks(db: Session) -> list[DownloadTaskResponse]:
    rows = db.execute(
        select(DownloadTask, SourceItem)
        .join(SourceItem, SourceItem.id == DownloadTask.source_item_id)
        .order_by(DownloadTask.created_at.desc(), DownloadTask.id.desc())
    ).all()
    return [_to_response(download, source_item) for download, source_item in rows]


def get_download_task(db: Session, download_id: int) -> tuple[DownloadTask, SourceItem] | None:
    row = db.execute(
        select(DownloadTask, SourceItem)
        .join(SourceItem, SourceItem.id == DownloadTask.source_item_id)
        .where(DownloadTask.id == download_id)
    ).first()
    if row is None:
        return None
    download, source_item = row
    return download, source_item


def create_download_task(db: Session, item_id: int) -> DownloadTaskResponse:
    source_item = db.get(SourceItem, item_id)
    if source_item is None:
        raise LookupError("资源不存在")

    confirmed_match = db.scalar(
        select(MediaMatch).where(
            MediaMatch.source_item_id == item_id,
            MediaMatch.status == "confirmed",
        )
    )
    if confirmed_match is None:
        raise ValueError(MATCH_REQUIRED_MESSAGE)

    existing = db.scalar(select(DownloadTask).where(DownloadTask.source_item_id == item_id))
    if existing is not None:
        raise ValueError("下载任务已存在")

    settings = get_or_create_settings(db)
    provider = settings.download_provider or "qbittorrent"
    torrent_hash: str | None = None
    provider_task_id: str | None = None
    if provider == "nas115":
        service_url, token = _nas115_credentials(settings)
        provider_task_id = add_nas115_magnet_task(
            service_url=service_url,
            token=token,
            magnet_uri=source_item.magnet_uri,
        )
    else:
        url, username, password = _settings_credentials(settings)
        torrent_hash = add_paused_magnet(
            url=url,
            username=username,
            password=password,
            magnet_uri=source_item.magnet_uri,
            save_path=settings.download_dir,
        )
    download = DownloadTask(
        source_item_id=source_item.id,
        qbittorrent_hash=torrent_hash or None,
        provider=provider,
        provider_task_id=provider_task_id,
        magnet_uri=source_item.magnet_uri,
        save_path=settings.download_dir,
        status="submitted",
        progress=0,
        error_message=None,
    )
    db.add(download)
    db.commit()
    db.refresh(download)
    return _to_response(download, source_item)


def refresh_download_task(db: Session, download_id: int) -> DownloadTaskResponse:
    result = get_download_task(db, download_id)
    if result is None:
        raise LookupError("下载任务不存在")

    download, source_item = result
    previous_status = download.status
    settings = get_or_create_settings(db)
    if download.provider == "nas115":
        if not download.provider_task_id:
            raise ValueError("NAS 115 服务尚未返回任务编号，请稍后刷新")
        service_url, token = _nas115_credentials(settings)
        status_data = get_nas115_task_status(
            service_url=service_url,
            token=token,
            task_id=download.provider_task_id,
        )
    else:
        if not download.qbittorrent_hash:
            raise ValueError(HASH_PENDING_MESSAGE)
        url, username, password = _settings_credentials(settings)
        status_data = get_torrent_status(
            url=url,
            username=username,
            password=password,
            torrent_hash=download.qbittorrent_hash,
        )
    download.status = str(status_data.get("status", download.status))
    progress = status_data.get("progress", download.progress)
    download.progress = float(progress) if isinstance(progress, int | float) else download.progress
    error_message = status_data.get("error_message")
    download.error_message = str(error_message) if error_message else None
    db.add(download)
    db.commit()
    db.refresh(download)
    if download.status == "completed" and previous_status != "completed":
        try:
            from app.services.rename_service import handle_download_completed_auto_rename

            handle_download_completed_auto_rename(db, download.id)
        except Exception as exc:  # noqa: BLE001
            download.error_message = f"自动重命名失败：{exc}"
            db.add(download)
            db.commit()
            db.refresh(download)
    return _to_response(download, source_item)


def delete_download_task(db: Session, download_id: int) -> None:
    download = db.get(DownloadTask, download_id)
    if download is None:
        raise LookupError("下载任务不存在")
    db.delete(download)
    db.commit()

import os
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    DownloadFile,
    DownloadTask,
    ImportFileAction,
    ImportJob,
    RenamePreview,
)
from app.services.settings_service import get_or_create_settings
from app.utils.path_guard import ensure_parent_dir, ensure_target_inside, resolve_inside

PREVIEW_REQUIRED_MESSAGE = "请先生成命名预览。"
SOURCE_MISSING_MESSAGE = "源文件不存在"
TARGET_EXISTS_MESSAGE = "目标文件已存在"
FILE_OPERATION_FAILED_MESSAGE = "文件操作失败，请检查目录权限。"


def list_import_jobs(db: Session) -> list[ImportJob]:
    return list(
        db.scalars(select(ImportJob).order_by(ImportJob.created_at.desc(), ImportJob.id.desc()))
    )


def get_import_job(db: Session, import_id: int) -> ImportJob:
    import_job = db.get(ImportJob, import_id)
    if import_job is None:
        raise LookupError("入库任务不存在")
    return import_job


def list_import_file_actions(db: Session, import_id: int) -> list[ImportFileAction]:
    get_import_job(db, import_id)
    return list(
        db.scalars(
            select(ImportFileAction)
            .where(ImportFileAction.import_job_id == import_id)
            .order_by(ImportFileAction.id)
        )
    )


def execute_import(db: Session, download_id: int, mode: str = "hardlink") -> ImportJob:
    if mode not in {"hardlink", "copy"}:
        raise ValueError("入库方式不支持")
    download = db.get(DownloadTask, download_id)
    if download is None:
        raise LookupError("下载任务不存在")
    settings = get_or_create_settings(db)
    preview_rows = _preview_rows(db, download_id)
    if not preview_rows:
        raise ValueError(PREVIEW_REQUIRED_MESSAGE)

    import_job = ImportJob(download_task_id=download.id, status="pending", mode=mode)
    db.add(import_job)
    db.flush()

    eligible_rows = [
        (preview, download_file)
        for preview, download_file in preview_rows
        if not preview.conflict and download_file.selected
    ]
    completed_files = 0
    failed_messages: list[str] = []
    for preview, download_file in eligible_rows:
        action = ImportFileAction(
            import_job_id=import_job.id,
            download_file_id=download_file.id,
            source_path="",
            target_path=preview.target_path,
            action_type=mode,
            status="pending",
        )
        db.add(action)
        _execute_file_action(
            action=action,
            download=download,
            preview=preview,
            media_library_dir=settings.media_library_dir,
            mode=mode,
        )
        if action.status == "completed":
            completed_files += 1
        elif action.error_message:
            failed_messages.append(action.error_message)

    import_job.total_files = len(eligible_rows)
    import_job.completed_files = completed_files
    import_job.status = "completed" if completed_files == len(eligible_rows) else "failed"
    import_job.error_message = "；".join(dict.fromkeys(failed_messages)) or None
    db.add(import_job)
    db.commit()
    db.refresh(import_job)
    return import_job


def rollback_import(db: Session, import_id: int) -> ImportJob:
    import_job = get_import_job(db, import_id)
    settings = get_or_create_settings(db)
    actions = list_import_file_actions(db, import_id)
    for action in actions:
        if action.status != "completed":
            continue
        try:
            target_path = ensure_target_inside(settings.media_library_dir, action.target_path)
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
            action.status = "rolled_back"
            action.error_message = None
        except ValueError as exc:
            action.status = "failed"
            action.error_message = str(exc)
        except OSError:
            action.status = "failed"
            action.error_message = FILE_OPERATION_FAILED_MESSAGE
        db.add(action)
    import_job.status = "rolled_back"
    db.add(import_job)
    db.commit()
    db.refresh(import_job)
    return import_job


def _preview_rows(db: Session, download_id: int) -> list[tuple[RenamePreview, DownloadFile]]:
    rows = db.execute(
        select(RenamePreview, DownloadFile)
        .join(DownloadFile, DownloadFile.id == RenamePreview.download_file_id)
        .where(DownloadFile.download_task_id == download_id)
        .order_by(DownloadFile.file_index)
    ).all()
    return [(preview, download_file) for preview, download_file in rows]


def _execute_file_action(
    *,
    action: ImportFileAction,
    download: DownloadTask,
    preview: RenamePreview,
    media_library_dir: str,
    mode: str,
) -> None:
    try:
        source_path = resolve_inside(download.save_path, preview.original_path)
        target_path = ensure_target_inside(media_library_dir, preview.target_path)
        action.source_path = str(source_path)
        action.target_path = str(target_path)
        if not source_path.exists():
            _fail_action(action, SOURCE_MISSING_MESSAGE)
            return
        if target_path.exists():
            _fail_action(action, TARGET_EXISTS_MESSAGE)
            return
        ensure_parent_dir(target_path)
        if mode == "copy":
            shutil.copy2(source_path, target_path)
            action.action_type = "copy"
        else:
            _hardlink_or_copy(source_path, target_path, action)
        action.status = "completed"
        action.error_message = None
    except ValueError as exc:
        _fail_action(action, str(exc))
    except OSError:
        _fail_action(action, FILE_OPERATION_FAILED_MESSAGE)


def _hardlink_or_copy(source_path: Path, target_path: Path, action: ImportFileAction) -> None:
    try:
        os.link(source_path, target_path)
        action.action_type = "hardlink"
    except OSError:
        shutil.copy2(source_path, target_path)
        action.action_type = "copy"


def _fail_action(action: ImportFileAction, message: str) -> None:
    action.status = "failed"
    action.error_message = message

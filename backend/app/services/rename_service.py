from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import (
    DownloadFile,
    DownloadTask,
    RenameAction,
    RenamePreview,
    RenameRule,
    SourceItem,
)
from app.integrations.nas115 import (
    NAS115_CAPABILITY_MISSING_MESSAGE,
)
from app.integrations.nas115 import (
    check_name_exists as check_nas115_name_exists,
)
from app.integrations.nas115 import (
    rename_file as rename_nas115_file,
)
from app.services.settings_service import get_or_create_settings
from app.utils.rename_parser import build_target_name, classify_rename_file, extract_episode_number
from app.utils.secrets import decrypt_secret

MISSING_115_RENAME_MESSAGE = "当前项目未发现可用的 115 重命名能力。"
LOW_CONFIDENCE_MESSAGE = "未能识别集数，请人工确认。"
CONFLICT_MESSAGE = "目标文件名已存在，不能覆盖。"
DEFAULT_TEMPLATE = "{clean_title} - {episode}{ext}"
SAFE_CONFIDENCE = 60
NAS115_NOT_CONFIGURED_MESSAGE = "请先启用并填写 NAS 115 服务地址"
UNSAFE_ROLLBACK_MESSAGE = "无法安全自动回滚，请在 115 网盘中手动检查。"


def rename_115_file(*, file_id: str, new_name: str) -> None:
    raise NotImplementedError(MISSING_115_RENAME_MESSAGE)


def get_or_create_rule(db: Session) -> RenameRule:
    rule = db.scalar(select(RenameRule).order_by(RenameRule.id).limit(1))
    if rule is not None:
        return rule
    rule = RenameRule(
        enabled=False,
        auto_execute=False,
        name_template=DEFAULT_TEMPLATE,
        episode_padding=2,
        remove_words="",
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def update_rule(db: Session, data: dict[str, object]) -> RenameRule:
    rule = get_or_create_rule(db)
    for field in ("enabled", "auto_execute", "name_template", "episode_padding", "remove_words"):
        if field in data and data[field] is not None:
            setattr(rule, field, data[field])
    rule.updated_at = datetime.utcnow()
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def list_actions(db: Session, download_id: int) -> list[RenameAction]:
    _download_or_404(db, download_id)
    return list(
        db.scalars(
            select(RenameAction)
            .where(RenameAction.task_id == download_id)
            .order_by(RenameAction.created_at.desc(), RenameAction.id.desc())
        )
    )


def list_previews(db: Session, download_id: int) -> list[RenamePreview]:
    _download_or_404(db, download_id)
    return list(
        db.scalars(
            select(RenamePreview)
            .join(DownloadFile, DownloadFile.id == RenamePreview.download_file_id)
            .where(DownloadFile.download_task_id == download_id)
            .order_by(DownloadFile.file_index)
        )
    )


def generate_previews(db: Session, download_id: int) -> list[RenamePreview]:
    download = _download_or_404(db, download_id)
    rule = get_or_create_rule(db)
    source_item = db.get(SourceItem, download.source_item_id)
    title = source_item.title if source_item is not None else "未命名任务"
    files = list(
        db.scalars(
            select(DownloadFile)
            .where(DownloadFile.download_task_id == download_id)
            .order_by(DownloadFile.file_index)
        )
    )
    file_ids = [file.id for file in files]
    if file_ids:
        db.execute(delete(RenamePreview).where(RenamePreview.download_file_id.in_(file_ids)))

    video_target_by_episode: dict[int, str] = {}
    planned: list[tuple[DownloadFile, str, int | None, int, str | None]] = []
    for download_file in files:
        episode = download_file.episode_number or extract_episode_number(download_file.name)
        confidence = _confidence_for(download_file, episode)
        warning = None if confidence >= SAFE_CONFIDENCE else LOW_CONFIDENCE_MESSAGE
        file_type = _file_type(download_file)
        target_name = _target_name_for(download_file, title, rule, episode)
        planned.append((download_file, target_name, episode, confidence, warning))
        if file_type == "video" and episode is not None:
            video_target_by_episode[episode] = target_name

    normalized: list[tuple[DownloadFile, str, int | None, int, str | None]] = []
    for download_file, target_name, episode, confidence, warning in planned:
        if _file_type(download_file) == "subtitle" and episode in video_target_by_episode:
            target_name = str(
                Path(video_target_by_episode[episode]).with_suffix(Path(download_file.name).suffix)
            )
        normalized.append((download_file, target_name, episode, confidence, warning))

    counts = Counter(
        (str(Path(download_file.name).parent), target_name)
        for download_file, target_name, _episode, confidence, _warning in normalized
        if confidence >= SAFE_CONFIDENCE
    )
    previews: list[RenamePreview] = []
    for download_file, target_name, episode, confidence, warning in normalized:
        parent = str(Path(download_file.name).parent)
        parent_id = None if parent == "." else parent
        conflict = counts[(parent, target_name)] > 1
        if conflict:
            warning = CONFLICT_MESSAGE
        preview = RenamePreview(
            download_file_id=download_file.id,
            task_id=download_id,
            file_id=download_file.provider_file_id or str(download_file.file_index),
            parent_id=parent_id,
            original_name=Path(download_file.name).name,
            target_name=target_name,
            original_path=download_file.name,
            target_path=str(Path(parent) / target_name) if parent != "." else target_name,
            file_size=download_file.size,
            file_type=_file_type(download_file),
            episode_number=episode,
            confidence=confidence,
            conflict=conflict,
            warning_message=warning,
            status="pending",
        )
        db.add(preview)
        previews.append(preview)

    db.commit()
    for preview in previews:
        db.refresh(preview)
    return list_previews(db, download_id)


def apply_rename(db: Session, download_id: int) -> list[RenameAction]:
    download = _download_or_404(db, download_id)
    nas115_context = _nas115_context(db, download) if download.provider == "nas115" else None
    previews = list_previews(db, download_id)
    actions: list[RenameAction] = []
    for preview in previews:
        if preview.conflict or preview.confidence < SAFE_CONFIDENCE or preview.status == "renamed":
            continue
        download_file = db.get(DownloadFile, preview.download_file_id)
        if download_file is None or not download_file.selected:
            continue
        action = RenameAction(
            preview_id=preview.id,
            task_id=download_id,
            file_id=preview.file_id or str(preview.download_file_id),
            old_name=preview.original_name or Path(preview.original_path).name,
            new_name=preview.target_name or Path(preview.target_path).name,
            old_parent_id=preview.parent_id,
            new_parent_id=preview.parent_id,
            action_type="rename",
            status="completed",
            error_message=None,
        )
        try:
            if nas115_context is None:
                rename_115_file(file_id=action.file_id, new_name=action.new_name)
            else:
                service_url, token = nas115_context
                if _nas115_name_exists(service_url, token, action.new_parent_id, action.new_name):
                    preview.conflict = True
                    preview.warning_message = CONFLICT_MESSAGE
                    db.add(preview)
                    continue
                rename_nas115_file(
                    service_url=service_url,
                    token=token,
                    file_id=action.file_id,
                    new_name=action.new_name,
                )
            preview.status = "renamed"
        except Exception as exc:  # noqa: BLE001
            action.status = "failed"
            action.error_message = _provider_error_message(exc)
            preview.status = "failed"
            preview.warning_message = action.error_message
        db.add(preview)
        db.add(action)
        actions.append(action)
    db.commit()
    for action in actions:
        db.refresh(action)
    return actions


def rollback_action(db: Session, action_id: int) -> RenameAction:
    action = db.get(RenameAction, action_id)
    if action is None:
        raise LookupError("重命名动作不存在")
    if action.status != "completed":
        raise ValueError(UNSAFE_ROLLBACK_MESSAGE)
    try:
        download = db.get(DownloadTask, action.task_id)
        if download is not None and download.provider == "nas115":
            service_url, token = _nas115_context(db, download)
            rename_nas115_file(
                service_url=service_url,
                token=token,
                file_id=action.file_id,
                new_name=action.old_name,
            )
        else:
            rename_115_file(file_id=action.file_id, new_name=action.old_name)
    except Exception as exc:  # noqa: BLE001
        action.status = "failed"
        action.error_message = UNSAFE_ROLLBACK_MESSAGE
        db.add(action)
        db.commit()
        raise ValueError(action.error_message) from exc
    action.status = "rolled_back"
    action.updated_at = datetime.utcnow()
    preview = db.get(RenamePreview, action.preview_id)
    if preview is not None:
        preview.status = "rolled_back"
        db.add(preview)
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def run_auto_rename(
    db: Session,
    download_id: int,
) -> tuple[list[RenamePreview], list[RenameAction], list[str]]:
    rule = get_or_create_rule(db)
    previews = generate_previews(db, download_id)
    skipped: list[str] = []
    actions: list[RenameAction] = []
    if not rule.auto_execute:
        skipped.append("自动执行未开启，仅生成预览。")
        return previews, actions, skipped
    unsafe = [
        preview for preview in previews if preview.conflict or preview.confidence < SAFE_CONFIDENCE
    ]
    if unsafe:
        skipped.append("存在冲突或低可信预览，已跳过自动执行。")
        return previews, actions, skipped
    actions = apply_rename(db, download_id)
    return previews, actions, skipped


def handle_download_completed_auto_rename(db: Session, download_id: int) -> None:
    rule = get_or_create_rule(db)
    if not rule.enabled:
        return
    previews, actions, skipped = run_auto_rename(db, download_id)
    from app.services.log_service import write_operation_log

    write_operation_log(
        db,
        module="rename",
        message="下载完成后自动重命名已处理",
        detail=(
            f"下载任务编号：{download_id}，预览数量：{len(previews)}，"
            f"动作数量：{len(actions)}，跳过原因：{'；'.join(skipped) or '无'}"
        ),
    )


def _download_or_404(db: Session, download_id: int) -> DownloadTask:
    download = db.get(DownloadTask, download_id)
    if download is None:
        raise LookupError("下载任务不存在")
    return download


def _nas115_context(db: Session, download: DownloadTask) -> tuple[str, str | None]:
    settings = get_or_create_settings(db)
    if not settings.cloud115_enabled or not settings.cloud115_service_url:
        raise ValueError(NAS115_NOT_CONFIGURED_MESSAGE)
    return settings.cloud115_service_url, decrypt_secret(settings.cloud115_service_token)


def _nas115_name_exists(
    service_url: str,
    token: str | None,
    parent_id: str | None,
    name: str,
) -> bool:
    try:
        return check_nas115_name_exists(
            service_url=service_url,
            token=token,
            parent_id=parent_id,
            name=name,
        )
    except ValueError as exc:
        if str(exc) == NAS115_CAPABILITY_MISSING_MESSAGE:
            return False
        raise


def _file_type(download_file: DownloadFile) -> str:
    if download_file.file_type in {"video", "subtitle", "image", "document", "other"}:
        return download_file.file_type
    return classify_rename_file(download_file.name)


def _target_name_for(
    download_file: DownloadFile,
    title: str,
    rule: RenameRule,
    episode: int | None,
) -> str:
    path = Path(download_file.name)
    return build_target_name(
        title=title,
        original_name=path.stem,
        extension=path.suffix,
        episode_number=episode,
        template=rule.name_template,
        episode_padding=rule.episode_padding,
        remove_words=rule.remove_words,
    )


def _confidence_for(download_file: DownloadFile, episode: int | None) -> int:
    if episode is None:
        return 40
    if _file_type(download_file) in {"video", "subtitle"}:
        return 90
    return 70


def _provider_error_message(exc: Exception) -> str:
    text = str(exc) or MISSING_115_RENAME_MESSAGE
    if text == MISSING_115_RENAME_MESSAGE:
        return text
    return f"重命名失败：{text}"

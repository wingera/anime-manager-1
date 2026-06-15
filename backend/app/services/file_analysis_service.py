from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import AppSettings, DownloadFile, DownloadTask, MediaMatch, RenamePreview
from app.integrations.qbittorrent import get_torrent_files, set_file_priority
from app.services.download_service import HASH_PENDING_MESSAGE, QB_NOT_CONFIGURED_MESSAGE
from app.services.settings_service import get_or_create_settings
from app.utils.emby_naming import build_target_path
from app.utils.file_analyzer import (
    MIN_MAIN_VIDEO_SIZE,
    classify_file,
    guess_episode_from_filename,
    is_video_file,
    score_download_file,
)
from app.utils.secrets import decrypt_secret

MATCH_REQUIRED_MESSAGE = "请先确认资料匹配。"
HASH_PENDING_ANALYSIS_MESSAGE = f"{HASH_PENDING_MESSAGE}。"


def _settings_credentials(settings: AppSettings) -> tuple[str, str, str]:
    password = decrypt_secret(settings.qbittorrent_password)
    if not settings.qbittorrent_url or not settings.qbittorrent_username or not password:
        raise ValueError(QB_NOT_CONFIGURED_MESSAGE)
    return settings.qbittorrent_url, settings.qbittorrent_username, password


def _download_or_404(db: Session, download_id: int) -> DownloadTask:
    download = db.get(DownloadTask, download_id)
    if download is None:
        raise LookupError("下载任务不存在")
    return download


def _to_int(value: object, default: int = 0) -> int:
    return value if isinstance(value, int) else default


def _to_float(value: object, default: float = 0.0) -> float:
    return float(value) if isinstance(value, int | float) else default


def _file_name(data: dict[str, object]) -> str:
    name = data.get("name")
    return str(name) if name is not None else ""


def _selected_by_default(
    size: int,
    file_type: str,
    video_count: int,
    max_video_size: int,
) -> bool:
    if file_type == "subtitle":
        return True
    if file_type != "video":
        return False
    if video_count == 1:
        return True
    if size < MIN_MAIN_VIDEO_SIZE:
        return False
    return size == max_video_size or size >= MIN_MAIN_VIDEO_SIZE


def list_download_files(db: Session, download_id: int) -> list[DownloadFile]:
    _download_or_404(db, download_id)
    return list(
        db.scalars(
            select(DownloadFile)
            .where(DownloadFile.download_task_id == download_id)
            .order_by(DownloadFile.file_index)
        )
    )


def analyze_download_files(db: Session, download_id: int) -> list[DownloadFile]:
    download = _download_or_404(db, download_id)
    if not download.qbittorrent_hash:
        raise ValueError(HASH_PENDING_ANALYSIS_MESSAGE)

    settings = get_or_create_settings(db)
    url, username, password = _settings_credentials(settings)
    raw_files = get_torrent_files(
        url=url,
        username=username,
        password=password,
        torrent_hash=download.qbittorrent_hash,
    )
    video_sizes = [
        _to_int(data.get("size"))
        for data in raw_files
        if is_video_file(_file_name(data))
        and classify_file(_file_name(data), _to_int(data.get("size"))) == "video"
    ]
    video_count = len(video_sizes)
    max_video_size = max(video_sizes, default=0)

    results: list[DownloadFile] = []
    for fallback_index, data in enumerate(raw_files):
        file_index = _to_int(data.get("index"), fallback_index)
        name = _file_name(data)
        size = _to_int(data.get("size"))
        progress = _to_float(data.get("progress"))
        priority = _to_int(data.get("priority"), 1)
        file_type = classify_file(name, size)
        season_number, episode_number = guess_episode_from_filename(name)
        selected = _selected_by_default(size, file_type, video_count, max_video_size)

        download_file = db.scalar(
            select(DownloadFile).where(
                DownloadFile.download_task_id == download_id,
                DownloadFile.file_index == file_index,
            )
        )
        if download_file is None:
            download_file = DownloadFile(download_task_id=download_id, file_index=file_index)

        download_file.name = name
        download_file.size = size
        download_file.progress = progress
        download_file.priority = priority
        download_file.file_type = file_type
        download_file.selected = selected
        download_file.analysis_score = score_download_file(name, size)
        download_file.season_number = season_number
        download_file.episode_number = episode_number
        db.add(download_file)
        results.append(download_file)

    db.commit()
    for download_file in results:
        db.refresh(download_file)
    return list_download_files(db, download_id)


def update_download_file(db: Session, file_id: int, data: dict[str, Any]) -> DownloadFile:
    download_file = db.get(DownloadFile, file_id)
    if download_file is None:
        raise LookupError("下载文件不存在")
    for field in ("selected", "file_type", "season_number", "episode_number"):
        if field in data:
            setattr(download_file, field, data[field])
    db.add(download_file)
    db.commit()
    db.refresh(download_file)
    return download_file


def apply_file_priority(db: Session, download_id: int) -> list[DownloadFile]:
    download = _download_or_404(db, download_id)
    if not download.qbittorrent_hash:
        raise ValueError(HASH_PENDING_ANALYSIS_MESSAGE)

    files = list_download_files(db, download_id)
    settings = get_or_create_settings(db)
    url, username, password = _settings_credentials(settings)
    selected_indexes = [file.file_index for file in files if file.selected]
    unselected_indexes = [file.file_index for file in files if not file.selected]
    set_file_priority(
        url=url,
        username=username,
        password=password,
        torrent_hash=download.qbittorrent_hash,
        file_indexes=unselected_indexes,
        priority=0,
    )
    set_file_priority(
        url=url,
        username=username,
        password=password,
        torrent_hash=download.qbittorrent_hash,
        file_indexes=selected_indexes,
        priority=1,
    )
    for download_file in files:
        download_file.priority = 1 if download_file.selected else 0
        db.add(download_file)
    db.commit()
    return list_download_files(db, download_id)


def list_rename_previews(db: Session, download_id: int) -> list[RenamePreview]:
    _download_or_404(db, download_id)
    return list(
        db.scalars(
            select(RenamePreview)
            .join(DownloadFile, DownloadFile.id == RenamePreview.download_file_id)
            .where(DownloadFile.download_task_id == download_id)
            .order_by(DownloadFile.file_index)
        )
    )


def _confirmed_match(db: Session, download: DownloadTask) -> MediaMatch:
    match = db.scalar(
        select(MediaMatch).where(
            MediaMatch.source_item_id == download.source_item_id,
            MediaMatch.status == "confirmed",
        )
    )
    if match is None:
        raise ValueError(MATCH_REQUIRED_MESSAGE)
    return match


def generate_rename_previews(db: Session, download_id: int) -> list[RenamePreview]:
    download = _download_or_404(db, download_id)
    media_match = _confirmed_match(db, download)
    settings = get_or_create_settings(db)
    selected_files = list(
        db.scalars(
            select(DownloadFile)
            .where(
                DownloadFile.download_task_id == download_id,
                DownloadFile.selected.is_(True),
                DownloadFile.file_type.in_(("video", "subtitle")),
            )
            .order_by(DownloadFile.file_index)
        )
    )
    video_files = [file for file in selected_files if file.file_type == "video"]
    subtitle_files = [file for file in selected_files if file.file_type == "subtitle"]

    all_task_file_ids = list(
        db.scalars(
            select(DownloadFile.id).where(DownloadFile.download_task_id == download_id)
        )
    )
    if all_task_file_ids:
        db.execute(delete(RenamePreview).where(RenamePreview.download_file_id.in_(all_task_file_ids)))

    target_paths: list[str] = []
    previews: list[RenamePreview] = []
    video_preview_by_id: dict[int, RenamePreview] = {}
    for download_file in video_files:
        extension = Path(download_file.name).suffix
        season_number = download_file.season_number or media_match.season_number
        episode_number = download_file.episode_number or media_match.episode_number
        target_path = build_target_path(
            media_library_dir=settings.media_library_dir,
            title=media_match.title or "未命名",
            year=media_match.year,
            tmdb_id=media_match.tmdb_id,
            season_number=season_number,
            episode_number=episode_number,
            episode_title=media_match.episode_title,
            extension=extension,
        )
        target_paths.append(target_path)
        preview = RenamePreview(
            download_file_id=download_file.id,
            task_id=download_id,
            file_id=str(download_file.file_index),
            parent_id=None,
            original_name=Path(download_file.name).name,
            target_name=Path(target_path).name,
            original_path=download_file.name,
            target_path=target_path,
            file_size=download_file.size,
            file_type=download_file.file_type,
            episode_number=episode_number,
            confidence=90 if episode_number is not None else 50,
            conflict=False,
            warning_message=None,
            status="pending",
        )
        db.add(preview)
        previews.append(preview)
        video_preview_by_id[download_file.id] = preview

    unmatched_subtitle_ids: set[int] = set()
    for download_file in subtitle_files:
        extension = Path(download_file.name).suffix
        matched_video = _match_subtitle_video(download_file, video_files)
        if matched_video is None:
            unmatched_subtitle_ids.add(download_file.id)
            season_number = download_file.season_number or media_match.season_number
            episode_number = download_file.episode_number or media_match.episode_number
            target_path = build_target_path(
                media_library_dir=settings.media_library_dir,
                title=media_match.title or "未命名",
                year=media_match.year,
                tmdb_id=media_match.tmdb_id,
                season_number=season_number,
                episode_number=episode_number,
                episode_title=media_match.episode_title,
                extension=extension,
            )
            warning_message = "字幕未能自动匹配正片，请人工确认。"
        else:
            video_preview = video_preview_by_id[matched_video.id]
            target_path = str(Path(video_preview.target_path).with_suffix(extension))
            warning_message = None
        target_paths.append(target_path)
        preview = RenamePreview(
            download_file_id=download_file.id,
            task_id=download_id,
            file_id=str(download_file.file_index),
            parent_id=None,
            original_name=Path(download_file.name).name,
            target_name=Path(target_path).name,
            original_path=download_file.name,
            target_path=target_path,
            file_size=download_file.size,
            file_type=download_file.file_type,
            episode_number=episode_number,
            confidence=90 if episode_number is not None else 50,
            conflict=False,
            warning_message=warning_message,
            status="pending",
        )
        db.add(preview)
        previews.append(preview)

    counts = Counter(target_paths)
    for preview in previews:
        if preview.download_file_id in unmatched_subtitle_ids:
            preview.conflict = False
            continue
        path_exists = Path(preview.target_path).exists()
        duplicate = counts[preview.target_path] > 1
        preview.conflict = path_exists or duplicate
        if duplicate:
            preview.warning_message = "目标路径重复，请手动调整季集信息。"
        elif path_exists:
            preview.warning_message = "目标路径已存在，请确认是否冲突。"

    db.commit()
    for preview in previews:
        db.refresh(preview)
    return list_rename_previews(db, download_id)


def _match_subtitle_video(
    subtitle_file: DownloadFile,
    video_files: list[DownloadFile],
) -> DownloadFile | None:
    subtitle_path = Path(subtitle_file.name)
    subtitle_parent = subtitle_path.parent
    subtitle_stem = subtitle_path.stem.lower()
    subtitle_episode = subtitle_file.episode_number

    def same_parent(video_file: DownloadFile) -> bool:
        return Path(video_file.name).parent == subtitle_parent

    def same_stem(video_file: DownloadFile) -> bool:
        return Path(video_file.name).stem.lower() == subtitle_stem

    def same_episode(video_file: DownloadFile) -> bool:
        return (
            subtitle_episode is not None
            and video_file.episode_number is not None
            and subtitle_episode == video_file.episode_number
        )

    for video_file in video_files:
        if same_parent(video_file) and same_stem(video_file):
            return video_file
    for video_file in video_files:
        if same_parent(video_file) and same_episode(video_file):
            return video_file
    for video_file in video_files:
        if same_stem(video_file):
            return video_file
    for video_file in video_files:
        if same_episode(video_file):
            return video_file
    return None

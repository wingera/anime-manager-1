from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    authorization_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    fetch_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    hash_pattern: Mapped[str] = mapped_column(Text, default="", nullable=False)
    title_cleanup_rule: Mapped[str] = mapped_column(Text, default="", nullable=False)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SourceSite(Base):
    __tablename__ = "source_sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), default="webpage", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auth_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    fetch_interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    hash_pattern: Mapped[str] = mapped_column(Text, default="", nullable=False)
    title_cleanup_rules: Mapped[str] = mapped_column(Text, default="", nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SourceItem(Base):
    __tablename__ = "source_items"
    __table_args__ = (UniqueConstraint("info_hash", name="uq_source_items_info_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("source_sites.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    info_hash: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    magnet_uri: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class MediaMatch(Base):
    __tablename__ = "media_matches"
    __table_args__ = (UniqueConstraint("source_item_id", name="uq_media_matches_source_item_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_item_id: Mapped[int] = mapped_column(
        ForeignKey("source_items.id"),
        nullable=False,
        index=True,
    )
    tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tmdb_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    tmdb_language: Mapped[str] = mapped_column(String(20), default="zh-CN", nullable=False)
    tmdb_region: Mapped[str] = mapped_column(String(20), default="CN", nullable=False)
    qbittorrent_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    qbittorrent_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qbittorrent_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_dir: Mapped[str] = mapped_column(Text, default="/downloads", nullable=False)
    media_library_dir: Mapped[str] = mapped_column(Text, default="/media", nullable=False)
    matching_threshold: Mapped[int] = mapped_column(Integer, default=85, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class Resource(Base):
    __tablename__ = "resources"
    __table_args__ = (UniqueConstraint("resource_hash", name="uq_resources_resource_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    resource_hash: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    magnet_uri: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="pending_review", nullable=False)
    safety_status: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MetadataMatch(Base):
    __tablename__ = "metadata_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    resource_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    original_title: Mapped[str] = mapped_column(Text, default="", nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DownloadTask(Base):
    __tablename__ = "download_tasks"
    __table_args__ = (UniqueConstraint("source_item_id", name="uq_download_tasks_source_item_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_item_id: Mapped[int] = mapped_column(
        ForeignKey("source_items.id"),
        nullable=False,
        index=True,
    )
    qbittorrent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    magnet_uri: Mapped[str] = mapped_column(Text, nullable=False)
    save_path: Mapped[str] = mapped_column(Text, default="/downloads", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class DownloadFile(Base):
    __tablename__ = "download_files"
    __table_args__ = (
        UniqueConstraint("download_task_id", "file_index", name="uq_download_files_task_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    download_task_id: Mapped[int] = mapped_column(
        ForeignKey("download_tasks.id"),
        nullable=False,
        index=True,
    )
    file_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    file_type: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    analysis_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    season_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class RenamePreview(Base):
    __tablename__ = "rename_previews"
    __table_args__ = (
        UniqueConstraint("download_file_id", name="uq_rename_previews_download_file_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    download_file_id: Mapped[int] = mapped_column(
        ForeignKey("download_files.id"),
        nullable=False,
        index=True,
    )
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_path: Mapped[str] = mapped_column(Text, nullable=False)
    conflict: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warning_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    download_task_id: Mapped[int] = mapped_column(
        ForeignKey("download_tasks.id"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    mode: Mapped[str] = mapped_column(String(40), default="hardlink", nullable=False)
    total_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class ImportFileAction(Base):
    __tablename__ = "import_file_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_job_id: Mapped[int] = mapped_column(
        ForeignKey("import_jobs.id"),
        nullable=False,
        index=True,
    )
    download_file_id: Mapped[int] = mapped_column(
        ForeignKey("download_files.id"),
        nullable=False,
        index=True,
    )
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_path: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(String(40), default="hardlink", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    level: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    module: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class MediaFile(Base):
    __tablename__ = "media_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    download_task_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_path: Mapped[str] = mapped_column(Text, default="", nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_type: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False)
    season_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_score: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    action: Mapped[str] = mapped_column(String(40), default="pending_review", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

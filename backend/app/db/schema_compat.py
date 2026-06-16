from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def prepare_download_tasks_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if not inspector.has_table("download_tasks"):
        return

    columns = {column["name"] for column in inspector.get_columns("download_tasks")}
    if "source_item_id" in columns:
        return

    legacy_exists = inspector.has_table("download_tasks_legacy")
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX IF EXISTS ix_download_tasks_resource_id"))
        connection.execute(text("DROP INDEX IF EXISTS ix_download_tasks_id"))
        if legacy_exists:
            connection.execute(text("DROP TABLE download_tasks"))
        else:
            connection.execute(text("ALTER TABLE download_tasks RENAME TO download_tasks_legacy"))


def prepare_source_sites_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if not inspector.has_table("source_sites"):
        return

    columns = {column["name"] for column in inspector.get_columns("source_sites")}
    if "scan_detail_pages" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE source_sites "
                "ADD COLUMN scan_detail_pages BOOLEAN NOT NULL DEFAULT 0"
            )
        )


def prepare_app_settings_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    if not inspector.has_table("app_settings"):
        return

    with engine.begin() as connection:
        columns = {column["name"] for column in inspector.get_columns("app_settings")}
        additions = {
            "tmdb_include_adult": "BOOLEAN NOT NULL DEFAULT 0",
            "download_provider": "VARCHAR(40) NOT NULL DEFAULT 'qbittorrent'",
            "cloud115_enabled": "BOOLEAN NOT NULL DEFAULT 0",
            "cloud115_service_url": "TEXT NOT NULL DEFAULT 'http://192.168.1.19:9527'",
            "cloud115_service_token": "TEXT",
            "metadata_proxy_type": "VARCHAR(20) NOT NULL DEFAULT 'none'",
            "metadata_proxy_host": "TEXT",
            "metadata_proxy_port": "INTEGER",
            "metadata_proxy_username": "VARCHAR(255)",
            "metadata_proxy_password": "TEXT",
        }
        for column, definition in additions.items():
            if column not in columns:
                connection.execute(
                    text(f"ALTER TABLE app_settings ADD COLUMN {column} {definition}")
                )


def prepare_provider_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    with engine.begin() as connection:
        if inspector.has_table("download_tasks"):
            task_columns = {column["name"] for column in inspector.get_columns("download_tasks")}
            task_additions = {
                "provider": "VARCHAR(40) NOT NULL DEFAULT 'qbittorrent'",
                "provider_task_id": "VARCHAR(120)",
            }
            for column, definition in task_additions.items():
                if column not in task_columns:
                    connection.execute(
                        text(f"ALTER TABLE download_tasks ADD COLUMN {column} {definition}")
                    )

        if inspector.has_table("download_files"):
            file_columns = {column["name"] for column in inspector.get_columns("download_files")}
            file_additions = {
                "provider_file_id": "VARCHAR(120)",
                "parent_id": "VARCHAR(120)",
            }
            for column, definition in file_additions.items():
                if column not in file_columns:
                    connection.execute(
                        text(f"ALTER TABLE download_files ADD COLUMN {column} {definition}")
                    )


def prepare_rename_schema(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    with engine.begin() as connection:
        if inspector.has_table("rename_previews"):
            columns = {column["name"] for column in inspector.get_columns("rename_previews")}
            additions = {
                "task_id": "INTEGER",
                "file_id": "VARCHAR(120)",
                "parent_id": "VARCHAR(120)",
                "original_name": "TEXT NOT NULL DEFAULT ''",
                "target_name": "TEXT NOT NULL DEFAULT ''",
                "file_size": "INTEGER NOT NULL DEFAULT 0",
                "file_type": "VARCHAR(40) NOT NULL DEFAULT 'other'",
                "episode_number": "INTEGER",
                "confidence": "INTEGER NOT NULL DEFAULT 0",
                "status": "VARCHAR(40) NOT NULL DEFAULT 'pending'",
            }
            for column, definition in additions.items():
                if column not in columns:
                    connection.execute(
                        text(f"ALTER TABLE rename_previews ADD COLUMN {column} {definition}")
                    )

        if not inspector.has_table("rename_rules"):
            connection.execute(
                text(
                    """
                    CREATE TABLE rename_rules (
                        id INTEGER NOT NULL PRIMARY KEY,
                        enabled BOOLEAN NOT NULL DEFAULT 0,
                        auto_execute BOOLEAN NOT NULL DEFAULT 0,
                        name_template TEXT NOT NULL DEFAULT '{clean_title} - {episode}{ext}',
                        episode_padding INTEGER NOT NULL DEFAULT 2,
                        remove_words TEXT NOT NULL DEFAULT '',
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX ix_rename_rules_id ON rename_rules (id)"))

        if not inspector.has_table("rename_actions"):
            connection.execute(
                text(
                    """
                    CREATE TABLE rename_actions (
                        id INTEGER NOT NULL PRIMARY KEY,
                        preview_id INTEGER NOT NULL REFERENCES rename_previews (id),
                        task_id INTEGER NOT NULL REFERENCES download_tasks (id),
                        file_id VARCHAR(120) NOT NULL,
                        old_name TEXT NOT NULL,
                        new_name TEXT NOT NULL,
                        old_parent_id VARCHAR(120),
                        new_parent_id VARCHAR(120),
                        action_type VARCHAR(40) NOT NULL DEFAULT 'rename',
                        status VARCHAR(40) NOT NULL DEFAULT 'completed',
                        error_message TEXT,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL
                    )
                    """
                )
            )
            connection.execute(text("CREATE INDEX ix_rename_actions_id ON rename_actions (id)"))
            connection.execute(
                text("CREATE INDEX ix_rename_actions_preview_id ON rename_actions (preview_id)")
            )
            connection.execute(
                text("CREATE INDEX ix_rename_actions_task_id ON rename_actions (task_id)")
            )

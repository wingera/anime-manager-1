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

    columns = {column["name"] for column in inspector.get_columns("app_settings")}
    if "tmdb_include_adult" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE app_settings "
                "ADD COLUMN tmdb_include_adult BOOLEAN NOT NULL DEFAULT 0"
            )
        )

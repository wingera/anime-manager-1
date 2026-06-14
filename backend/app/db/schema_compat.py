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

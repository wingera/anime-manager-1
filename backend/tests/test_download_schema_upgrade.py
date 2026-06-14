from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.schema_compat import prepare_download_tasks_schema


def _legacy_engine() -> Engine:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE download_tasks (
                    id INTEGER NOT NULL PRIMARY KEY,
                    resource_id INTEGER NOT NULL,
                    torrent_hash VARCHAR(64) NOT NULL,
                    save_path TEXT NOT NULL,
                    progress FLOAT NOT NULL,
                    status VARCHAR(40) NOT NULL,
                    error_message TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        connection.execute(
            text("CREATE INDEX ix_download_tasks_resource_id ON download_tasks (resource_id)")
        )
        connection.execute(text("CREATE INDEX ix_download_tasks_id ON download_tasks (id)"))
    return engine


def test_prepare_download_tasks_schema_replaces_legacy_table() -> None:
    engine = _legacy_engine()

    prepare_download_tasks_schema(engine)
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("download_tasks")}
    assert "source_item_id" in columns
    assert "qbittorrent_hash" in columns
    assert "magnet_uri" in columns
    assert "resource_id" not in columns
    assert inspector.has_table("download_tasks_legacy")

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

test_data_dir = Path("/tmp/anime_manager_backend_tests")
os.environ["DATA_DIR"] = str(test_data_dir)
os.environ["DATABASE_URL"] = f"sqlite:///{test_data_dir / 'app.db'}"

from app.db.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


def _test_engine() -> Engine:
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture()
def db_session() -> Generator[Session]:
    engine = _test_engine()
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient]:
    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
        app.dependency_overrides.clear()

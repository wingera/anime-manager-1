from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_settings
from app.db import models as _models  # noqa: F401
from app.db.database import Base, engine
from app.db.schema_compat import prepare_download_tasks_schema
from app.routers.backup import router as backup_router
from app.routers.dashboard import router as dashboard_router
from app.routers.diagnostics import router as diagnostics_router
from app.routers.downloads import router as downloads_router
from app.routers.file_analysis import router as file_analysis_router
from app.routers.health import router as health_router
from app.routers.imports import router as imports_router
from app.routers.logs import router as logs_router
from app.routers.matching import router as matching_router
from app.routers.settings import router as settings_router
from app.routers.setup import router as setup_router
from app.routers.sources import router as sources_router
from app.utils.secrets import ensure_secret_key_available

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    ensure_secret_key_available()
    prepare_download_tasks_schema(engine)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
app.include_router(setup_router)
app.include_router(backup_router)
app.include_router(diagnostics_router)
app.include_router(settings_router)
app.include_router(sources_router)
app.include_router(matching_router)
app.include_router(downloads_router)
app.include_router(file_analysis_router)
app.include_router(imports_router)
app.include_router(logs_router)
app.include_router(dashboard_router)

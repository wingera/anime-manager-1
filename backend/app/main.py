from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_settings
from app.db import models as _models  # noqa: F401
from app.db.database import Base, engine
from app.db.schema_compat import prepare_download_tasks_schema
from app.routers.downloads import router as downloads_router
from app.routers.file_analysis import router as file_analysis_router
from app.routers.health import router as health_router
from app.routers.matching import router as matching_router
from app.routers.settings import router as settings_router
from app.routers.sources import router as sources_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    prepare_download_tasks_schema(engine)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
app.include_router(settings_router)
app.include_router(sources_router)
app.include_router(matching_router)
app.include_router(downloads_router)
app.include_router(file_analysis_router)

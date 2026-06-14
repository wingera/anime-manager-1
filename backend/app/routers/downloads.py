from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.downloads import (
    DownloadTaskDeleteResponse,
    DownloadTaskListResponse,
    DownloadTaskMessageResponse,
)
from app.services.download_service import (
    create_download_task,
    delete_download_task,
    list_download_tasks,
    refresh_download_task,
)

router = APIRouter(tags=["下载队列"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/api/downloads", response_model=DownloadTaskListResponse)
def read_downloads(db: DbSession) -> DownloadTaskListResponse:
    return DownloadTaskListResponse(
        message="下载任务列表获取成功",
        downloads=list_download_tasks(db),
    )


@router.post(
    "/api/source-items/{item_id}/download",
    response_model=DownloadTaskMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_download(item_id: int, db: DbSession) -> DownloadTaskMessageResponse:
    try:
        download = create_download_task(db, item_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DownloadTaskMessageResponse(message="下载任务已创建", download=download)


@router.post("/api/downloads/{download_id}/refresh", response_model=DownloadTaskMessageResponse)
def refresh_download(download_id: int, db: DbSession) -> DownloadTaskMessageResponse:
    try:
        download = refresh_download_task(db, download_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DownloadTaskMessageResponse(message="下载任务状态已刷新", download=download)


@router.delete("/api/downloads/{download_id}", response_model=DownloadTaskDeleteResponse)
def remove_download(download_id: int, db: DbSession) -> DownloadTaskDeleteResponse:
    try:
        delete_download_task(db, download_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DownloadTaskDeleteResponse(message="下载任务记录已删除")

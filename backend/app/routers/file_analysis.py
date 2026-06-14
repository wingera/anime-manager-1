from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.file_analysis import (
    DownloadFileListResponse,
    DownloadFileMessageResponse,
    DownloadFileResponse,
    DownloadFileUpdateRequest,
    FileAnalysisMessageResponse,
    RenamePreviewListResponse,
    RenamePreviewResponse,
    SimpleMessageResponse,
)
from app.services.file_analysis_service import (
    analyze_download_files,
    apply_file_priority,
    generate_rename_previews,
    list_download_files,
    list_rename_previews,
    update_download_file,
)

router = APIRouter(tags=["文件分析"])
DbSession = Annotated[Session, Depends(get_db)]


def _file_responses(files: Iterable[object]) -> list[DownloadFileResponse]:
    return [DownloadFileResponse.model_validate(file) for file in files]


def _preview_responses(previews: Iterable[object]) -> list[RenamePreviewResponse]:
    return [RenamePreviewResponse.model_validate(preview) for preview in previews]


@router.get("/api/downloads/{download_id}/files", response_model=DownloadFileListResponse)
def read_download_files(download_id: int, db: DbSession) -> DownloadFileListResponse:
    try:
        files = list_download_files(db, download_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DownloadFileListResponse(message="下载文件列表获取成功", files=_file_responses(files))


@router.post(
    "/api/downloads/{download_id}/files/analyze",
    response_model=FileAnalysisMessageResponse,
)
def analyze_files(download_id: int, db: DbSession) -> FileAnalysisMessageResponse:
    try:
        files = analyze_download_files(db, download_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FileAnalysisMessageResponse(message="文件分析完成", files=_file_responses(files))


@router.put("/api/download-files/{file_id}", response_model=DownloadFileMessageResponse)
def update_file(
    file_id: int,
    payload: DownloadFileUpdateRequest,
    db: DbSession,
) -> DownloadFileMessageResponse:
    try:
        download_file = update_download_file(
            db,
            file_id,
            payload.model_dump(exclude_unset=True),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DownloadFileMessageResponse(
        message="下载文件已更新",
        file=DownloadFileResponse.model_validate(download_file),
    )


@router.post(
    "/api/downloads/{download_id}/files/apply-priority",
    response_model=SimpleMessageResponse,
)
def apply_priority(download_id: int, db: DbSession) -> SimpleMessageResponse:
    try:
        apply_file_priority(db, download_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SimpleMessageResponse(message="文件优先级已应用")


@router.get("/api/downloads/{download_id}/rename-preview", response_model=RenamePreviewListResponse)
def read_rename_preview(download_id: int, db: DbSession) -> RenamePreviewListResponse:
    try:
        previews = list_rename_previews(db, download_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RenamePreviewListResponse(
        message="命名预览获取成功",
        previews=_preview_responses(previews),
    )


@router.post(
    "/api/downloads/{download_id}/rename-preview",
    response_model=RenamePreviewListResponse,
)
def create_rename_preview(download_id: int, db: DbSession) -> RenamePreviewListResponse:
    try:
        previews = generate_rename_previews(db, download_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RenamePreviewListResponse(
        message="命名预览已生成",
        previews=_preview_responses(previews),
    )

from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.imports import (
    ImportFileActionResponse,
    ImportJobDetailResponse,
    ImportJobListResponse,
    ImportJobMessageResponse,
    ImportJobResponse,
    ImportRequest,
    ImportSimpleMessageResponse,
)
from app.services.import_service import (
    execute_import,
    get_import_job,
    list_import_file_actions,
    list_import_jobs,
    rollback_import,
)

router = APIRouter(tags=["入库记录"])
DbSession = Annotated[Session, Depends(get_db)]


def _job_response(import_job: object) -> ImportJobResponse:
    return ImportJobResponse.model_validate(import_job)


def _action_responses(actions: Iterable[object]) -> list[ImportFileActionResponse]:
    return [ImportFileActionResponse.model_validate(action) for action in actions]


@router.get("/api/imports", response_model=ImportJobListResponse)
def read_imports(db: DbSession) -> ImportJobListResponse:
    return ImportJobListResponse(
        message="入库记录获取成功",
        imports=[_job_response(import_job) for import_job in list_import_jobs(db)],
    )


@router.post("/api/downloads/{download_id}/import", response_model=ImportJobMessageResponse)
def run_import(
    download_id: int,
    db: DbSession,
    payload: ImportRequest | None = None,
) -> ImportJobMessageResponse:
    try:
        import_job = execute_import(db, download_id, mode=(payload.mode if payload else "hardlink"))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ImportJobMessageResponse(message="入库执行完成", import_job=_job_response(import_job))


@router.get("/api/imports/{import_id}", response_model=ImportJobDetailResponse)
def read_import_detail(import_id: int, db: DbSession) -> ImportJobDetailResponse:
    try:
        import_job = get_import_job(db, import_id)
        actions = list_import_file_actions(db, import_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ImportJobDetailResponse(
        message="入库详情获取成功",
        import_job=_job_response(import_job),
        actions=_action_responses(actions),
    )


@router.post("/api/imports/{import_id}/rollback", response_model=ImportSimpleMessageResponse)
def rollback_import_job(import_id: int, db: DbSession) -> ImportSimpleMessageResponse:
    try:
        rollback_import(db, import_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ImportSimpleMessageResponse(message="入库回滚完成")

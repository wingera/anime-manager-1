from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import SourceSite
from app.schemas.sources import (
    DeleteSourceResponse,
    SourceItemImportRequest,
    SourceItemImportResponse,
    SourceItemListResponse,
    SourceItemResponse,
    SourceSiteCreate,
    SourceSiteListResponse,
    SourceSiteMessageResponse,
    SourceSiteResponse,
    SourceSiteUpdate,
    SourceTestResponse,
)
from app.services.source_service import (
    SourceTestError,
    create_source,
    delete_source,
    get_source,
    import_source_items,
    list_source_items,
    list_sources,
    test_source,
    update_source,
)

router = APIRouter(tags=["来源管理"])
DbSession = Annotated[Session, Depends(get_db)]


def _get_source_or_404(db: Session, source_id: int) -> SourceSite:
    source = get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="来源不存在")
    return source


def _source_response(source: SourceSite) -> SourceSiteResponse:
    return SourceSiteResponse.model_validate(source)


@router.get("/api/sources", response_model=SourceSiteListResponse)
def read_sources(db: DbSession) -> SourceSiteListResponse:
    return SourceSiteListResponse(
        message="来源列表获取成功",
        sources=[_source_response(source) for source in list_sources(db)],
    )


@router.post(
    "/api/sources",
    response_model=SourceSiteMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_source(payload: SourceSiteCreate, db: DbSession) -> SourceSiteMessageResponse:
    try:
        source = create_source(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SourceSiteMessageResponse(message="来源已创建", source=_source_response(source))


@router.get("/api/sources/{source_id}", response_model=SourceSiteMessageResponse)
def read_source(source_id: int, db: DbSession) -> SourceSiteMessageResponse:
    return SourceSiteMessageResponse(
        message="来源详情获取成功",
        source=_source_response(_get_source_or_404(db, source_id)),
    )


@router.put("/api/sources/{source_id}", response_model=SourceSiteMessageResponse)
def save_source(
    source_id: int,
    payload: SourceSiteUpdate,
    db: DbSession,
) -> SourceSiteMessageResponse:
    source = _get_source_or_404(db, source_id)
    try:
        updated = update_source(db, source, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SourceSiteMessageResponse(message="来源已更新", source=_source_response(updated))


@router.delete("/api/sources/{source_id}", response_model=DeleteSourceResponse)
def remove_source(source_id: int, db: DbSession) -> DeleteSourceResponse:
    source = _get_source_or_404(db, source_id)
    delete_source(db, source)
    return DeleteSourceResponse(message="来源已删除")


@router.post("/api/sources/{source_id}/test", response_model=SourceTestResponse)
def preview_source(source_id: int, db: DbSession) -> SourceTestResponse:
    source = _get_source_or_404(db, source_id)
    try:
        found_count, items = test_source(db, source)
    except SourceTestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SourceTestResponse(
        message="来源测试完成",
        source_id=source_id,
        found_count=found_count,
        items=items,
    )


@router.post(
    "/api/sources/{source_id}/items",
    response_model=SourceItemImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_source_items(
    source_id: int,
    payload: SourceItemImportRequest,
    db: DbSession,
) -> SourceItemImportResponse:
    _get_source_or_404(db, source_id)
    try:
        created_count, skipped_count, items = import_source_items(
            db,
            source_id=source_id,
            items=[(item.title, item.url, item.info_hash) for item in payload.items],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return SourceItemImportResponse(
        message="资源已加入资源库",
        created_count=created_count,
        skipped_count=skipped_count,
        items=[SourceItemResponse.model_validate(item) for item in items],
    )


@router.get("/api/source-items", response_model=SourceItemListResponse)
def read_source_items(db: DbSession) -> SourceItemListResponse:
    return SourceItemListResponse(
        message="资源指纹列表获取成功",
        items=[SourceItemResponse.model_validate(item) for item in list_source_items(db)],
    )

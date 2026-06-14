from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.matching import (
    MediaMatchListResponse,
    MediaMatchMessageResponse,
    MediaMatchResponse,
    MediaMatchSaveRequest,
    TmdbSearchResponse,
)
from app.services.log_service import write_operation_log
from app.services.matching_service import (
    TmdbSearchError,
    get_source_item,
    list_media_matches,
    save_media_match,
    search_tmdb_candidates,
)

router = APIRouter(tags=["资料匹配"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/api/source-items/{item_id}/tmdb/search", response_model=TmdbSearchResponse)
def search_tmdb(item_id: int, db: DbSession) -> TmdbSearchResponse:
    item = get_source_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在")
    try:
        candidates = search_tmdb_candidates(db, item)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except TmdbSearchError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return TmdbSearchResponse(message="TMDB 搜索完成", candidates=candidates)


@router.put("/api/source-items/{item_id}/match", response_model=MediaMatchMessageResponse)
def save_match(
    item_id: int,
    payload: MediaMatchSaveRequest,
    db: DbSession,
) -> MediaMatchMessageResponse:
    item = get_source_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在")
    media_match = save_media_match(db, source_item_id=item.id, payload=payload)
    write_operation_log(
        db,
        module="matching",
        message="匹配信息已保存",
        detail=f"资源编号：{item.id}，匹配分：{media_match.match_score}",
    )
    return MediaMatchMessageResponse(
        message="匹配信息已保存",
        match=MediaMatchResponse.model_validate(media_match),
    )


@router.get("/api/matches", response_model=MediaMatchListResponse)
def read_matches(db: DbSession) -> MediaMatchListResponse:
    return MediaMatchListResponse(
        message="匹配列表获取成功",
        matches=[MediaMatchResponse.model_validate(item) for item in list_media_matches(db)],
    )

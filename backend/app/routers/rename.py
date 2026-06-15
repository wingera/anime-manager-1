from collections.abc import Iterable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.file_analysis import RenamePreviewListResponse, RenamePreviewResponse
from app.schemas.rename import (
    AutoRenameResponse,
    RenameActionListResponse,
    RenameActionResponse,
    RenameRuleMessageResponse,
    RenameRuleResponse,
    RenameRuleUpdateRequest,
)
from app.services.log_service import write_operation_log
from app.services.rename_service import (
    apply_rename,
    generate_previews,
    get_or_create_rule,
    list_actions,
    list_previews,
    rollback_action,
    run_auto_rename,
    update_rule,
)

router = APIRouter(tags=["自动重命名"])
DbSession = Annotated[Session, Depends(get_db)]


def _preview_responses(previews: Iterable[object]) -> list[RenamePreviewResponse]:
    return [RenamePreviewResponse.model_validate(preview) for preview in previews]


def _action_responses(actions: Iterable[object]) -> list[RenameActionResponse]:
    return [RenameActionResponse.model_validate(action) for action in actions]


@router.get("/api/rename/rule", response_model=RenameRuleMessageResponse)
def read_rename_rule(db: DbSession) -> RenameRuleMessageResponse:
    return RenameRuleMessageResponse(
        message="自动重命名规则获取成功",
        rule=RenameRuleResponse.model_validate(get_or_create_rule(db)),
    )


@router.put("/api/rename/rule", response_model=RenameRuleMessageResponse)
def save_rename_rule(
    payload: RenameRuleUpdateRequest,
    db: DbSession,
) -> RenameRuleMessageResponse:
    rule = update_rule(db, payload.model_dump(exclude_unset=True))
    write_operation_log(
        db,
        module="rename",
        message="自动重命名规则已保存",
        detail="规则已更新，未包含任何凭证内容。",
    )
    return RenameRuleMessageResponse(
        message="自动重命名规则已保存",
        rule=RenameRuleResponse.model_validate(rule),
    )


@router.get("/api/tasks/{task_id}/rename-preview", response_model=RenamePreviewListResponse)
def read_task_rename_preview(task_id: int, db: DbSession) -> RenamePreviewListResponse:
    try:
        previews = list_previews(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RenamePreviewListResponse(
        message="重命名预览获取成功",
        previews=_preview_responses(previews),
    )


@router.post("/api/tasks/{task_id}/rename-preview", response_model=RenamePreviewListResponse)
def create_task_rename_preview(task_id: int, db: DbSession) -> RenamePreviewListResponse:
    try:
        previews = generate_previews(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    write_operation_log(
        db,
        module="rename",
        message="重命名预览已生成",
        detail=f"下载任务编号：{task_id}，预览数量：{len(previews)}",
    )
    return RenamePreviewListResponse(
        message="重命名预览已生成",
        previews=_preview_responses(previews),
    )


@router.post("/api/tasks/{task_id}/rename-apply", response_model=RenameActionListResponse)
def apply_task_rename(task_id: int, db: DbSession) -> RenameActionListResponse:
    try:
        actions = apply_rename(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    write_operation_log(
        db,
        module="rename",
        message="重命名执行完成",
        detail=f"下载任务编号：{task_id}，动作数量：{len(actions)}",
    )
    return RenameActionListResponse(
        message="重命名执行完成",
        actions=_action_responses(actions),
    )


@router.get("/api/tasks/{task_id}/rename-actions", response_model=RenameActionListResponse)
def read_task_rename_actions(task_id: int, db: DbSession) -> RenameActionListResponse:
    try:
        actions = list_actions(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RenameActionListResponse(
        message="重命名记录获取成功",
        actions=_action_responses(actions),
    )


@router.post("/api/rename-actions/{action_id}/rollback", response_model=RenameActionListResponse)
def rollback_rename_action(action_id: int, db: DbSession) -> RenameActionListResponse:
    try:
        action = rollback_action(db, action_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    write_operation_log(
        db,
        module="rename",
        message="重命名动作已回滚",
        detail=f"重命名动作编号：{action_id}",
    )
    return RenameActionListResponse(
        message="重命名动作已回滚",
        actions=_action_responses([action]),
    )


@router.post("/api/tasks/{task_id}/auto-rename", response_model=AutoRenameResponse)
def run_task_auto_rename(task_id: int, db: DbSession) -> AutoRenameResponse:
    try:
        previews, actions, skipped_reasons = run_auto_rename(db, task_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    write_operation_log(
        db,
        module="rename",
        message="自动重命名已触发",
        detail=f"下载任务编号：{task_id}，动作数量：{len(actions)}",
    )
    return AutoRenameResponse(
        message="自动重命名已触发",
        previews=_preview_responses(previews),
        actions=_action_responses(actions),
        skipped_reasons=skipped_reasons,
    )

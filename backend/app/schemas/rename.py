from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.file_analysis import RenamePreviewResponse


class RenameRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    enabled: bool
    auto_execute: bool
    name_template: str
    episode_padding: int
    remove_words: str
    created_at: datetime
    updated_at: datetime


class RenameRuleUpdateRequest(BaseModel):
    enabled: bool | None = None
    auto_execute: bool | None = None
    name_template: str | None = Field(default=None, min_length=1, max_length=200)
    episode_padding: int | None = Field(default=None, ge=1, le=4)
    remove_words: str | None = Field(default=None, max_length=500)


class RenameRuleMessageResponse(BaseModel):
    message: str
    rule: RenameRuleResponse


class RenameActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    preview_id: int
    task_id: int
    file_id: str
    old_name: str
    new_name: str
    old_parent_id: str | None
    new_parent_id: str | None
    action_type: str
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class RenameActionListResponse(BaseModel):
    message: str
    actions: list[RenameActionResponse]


class AutoRenameResponse(BaseModel):
    message: str
    previews: list[RenamePreviewResponse]
    actions: list[RenameActionResponse]
    skipped_reasons: list[str]

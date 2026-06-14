from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TmdbCandidate(BaseModel):
    tmdb_id: int
    title: str
    original_title: str | None
    first_air_date: str | None
    overview: str
    poster_path: str | None
    match_score: float


class TmdbSearchResponse(BaseModel):
    message: str
    candidates: list[TmdbCandidate]


class MediaMatchSaveRequest(BaseModel):
    tmdb_id: int | None = None
    title: str | None = None
    original_title: str | None = None
    year: int | None = Field(default=None, ge=0)
    season_number: int | None = Field(default=None, ge=0)
    episode_number: int | None = Field(default=None, ge=0)
    episode_title: str | None = None
    match_score: float = Field(default=0, ge=0, le=100)
    status: str = "pending"


class MediaMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_item_id: int
    tmdb_id: int | None
    title: str | None
    original_title: str | None
    year: int | None
    season_number: int | None
    episode_number: int | None
    episode_title: str | None
    match_score: float
    status: str
    created_at: datetime
    updated_at: datetime


class MediaMatchMessageResponse(BaseModel):
    message: str
    match: MediaMatchResponse


class MediaMatchListResponse(BaseModel):
    message: str
    matches: list[MediaMatchResponse]

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["webpage", "manual", "rss"]


class SourceSiteBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1)
    source_type: SourceType = "webpage"
    enabled: bool = False
    auth_note: str = ""
    fetch_interval_minutes: int = Field(default=60, ge=1)
    hash_pattern: str = ""
    title_cleanup_rules: str = ""
    scan_detail_pages: bool = False


class SourceSiteCreate(SourceSiteBase):
    pass


class SourceSiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    url: str | None = Field(default=None, min_length=1)
    source_type: SourceType | None = None
    enabled: bool | None = None
    auth_note: str | None = None
    fetch_interval_minutes: int | None = Field(default=None, ge=1)
    hash_pattern: str | None = None
    title_cleanup_rules: str | None = None
    scan_detail_pages: bool | None = None


class SourceSiteResponse(SourceSiteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SourceSiteMessageResponse(BaseModel):
    message: str
    source: SourceSiteResponse


class SourceSiteListResponse(BaseModel):
    message: str
    sources: list[SourceSiteResponse]


class DeleteSourceResponse(BaseModel):
    message: str


class SourceItemCreate(BaseModel):
    source_id: int
    title: str = Field(min_length=1)
    url: str | None = None
    info_hash: str = Field(min_length=40, max_length=40)


class SourceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    title: str
    url: str | None
    info_hash: str
    magnet_uri: str
    published_at: datetime | None
    status: str
    created_at: datetime
    updated_at: datetime


class SourceItemListResponse(BaseModel):
    message: str
    items: list[SourceItemResponse]


class SourceItemImportItem(BaseModel):
    title: str = Field(min_length=1)
    url: str | None = None
    info_hash: str = Field(min_length=1)
    published_at: datetime | None = None


class SourceItemImportRequest(BaseModel):
    items: list[SourceItemImportItem] = Field(min_length=1)
    permission_confirmed: bool = False


class SourceItemImportResponse(BaseModel):
    message: str
    created_count: int
    skipped_count: int
    items: list[SourceItemResponse]


class SourcePreviewItem(BaseModel):
    title: str
    url: str | None
    info_hash: str
    magnet_uri: str
    published_at: datetime | None
    resource_group: str | None = None
    cover_image_url: str | None = None
    page_number: int = 1
    page_url: str | None = None


class SourcePaginationPage(BaseModel):
    page_number: int
    url: str


class SourcePagination(BaseModel):
    current_page: int
    total_pages: int
    pages: list[SourcePaginationPage]


class SourceScanFailure(BaseModel):
    url: str
    title: str | None = None
    message: str


class SourceTestRequest(BaseModel):
    page_number: int = Field(default=1, ge=1)


class SourceDetailScanRequest(BaseModel):
    url: str = Field(min_length=1)
    title: str | None = None
    page_number: int = Field(default=1, ge=1)


class SourceDetailScanResponse(BaseModel):
    message: str
    source_id: int
    found_count: int
    items: list[SourcePreviewItem]
    failed_page: SourceScanFailure | None = None


class SourceTestResponse(BaseModel):
    message: str
    source_id: int
    found_count: int
    items: list[SourcePreviewItem]
    warning_message: str | None
    pagination: SourcePagination
    failed_pages: list[SourceScanFailure] = Field(default_factory=list)

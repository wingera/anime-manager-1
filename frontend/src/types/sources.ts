export type SourceType = 'webpage' | 'manual' | 'rss'

export interface SourceSite {
  id: number
  name: string
  url: string
  source_type: SourceType
  enabled: boolean
  auth_note: string
  fetch_interval_minutes: number
  hash_pattern: string
  title_cleanup_rules: string
  scan_detail_pages: boolean
  last_checked_at: string | null
  created_at: string
  updated_at: string
}

export interface SourceFormPayload {
  name: string
  url: string
  source_type: SourceType
  enabled: boolean
  auth_note: string
  fetch_interval_minutes: number
  hash_pattern: string
  title_cleanup_rules: string
  scan_detail_pages: boolean
}

export type SourceUpdatePayload = Partial<SourceFormPayload>

export interface SourceMessageResponse {
  message: string
  source: SourceSite
}

export interface SourceListResponse {
  message: string
  sources: SourceSite[]
}

export interface DeleteSourceResponse {
  message: string
}

export interface SourcePreviewItem {
  title: string
  url: string | null
  info_hash: string
  magnet_uri: string
  published_at: string | null
  resource_group: string | null
  cover_image_url: string | null
  page_number: number
  page_url: string | null
}

export interface SourcePaginationPage {
  page_number: number
  url: string
}

export interface SourcePagination {
  current_page: number
  total_pages: number
  pages: SourcePaginationPage[]
}

export interface SourceTestRequest {
  page_number: number
}

export interface SourceDetailScanRequest {
  url: string
  title: string | null
  page_number: number
}

export interface SourceScanFailure {
  url: string
  title: string | null
  message: string
}

export interface SourceTestResponse {
  message: string
  source_id: number
  found_count: number
  items: SourcePreviewItem[]
  warning_message: string | null
  pagination: SourcePagination
  failed_pages: SourceScanFailure[]
}

export interface SourceDetailScanResponse {
  message: string
  source_id: number
  found_count: number
  items: SourcePreviewItem[]
  failed_page: SourceScanFailure | null
}

export interface SourceItem {
  id: number
  source_id: number
  title: string
  url: string | null
  info_hash: string
  magnet_uri: string
  published_at: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface SourceItemListResponse {
  message: string
  items: SourceItem[]
}

export interface SourceItemImportRequest {
  items: SourcePreviewItem[]
  permission_confirmed: boolean
}

export interface SourceItemImportResponse {
  message: string
  created_count: number
  skipped_count: number
  items: SourceItem[]
}

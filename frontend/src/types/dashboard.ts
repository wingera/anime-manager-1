import type { OperationLog } from './logs'

export interface DashboardSummary {
  sources_count: number
  source_items_count: number
  matches_count: number
  confirmed_matches_count: number
  downloads_count: number
  download_files_count: number
  rename_previews_count: number
  imports_count: number
  failed_imports_count: number
  latest_logs: OperationLog[]
}

export interface DashboardSummaryResponse {
  message: string
  summary: DashboardSummary
}

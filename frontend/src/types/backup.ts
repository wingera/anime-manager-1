export interface BackupSettings {
  tmdb_language: string
  tmdb_region: string
  has_tmdb_api_key: boolean
  qbittorrent_url: string | null
  qbittorrent_username: string | null
  has_qbittorrent_password: boolean
  download_dir: string
  media_library_dir: string
  matching_threshold: number
}

export interface BackupSource {
  name: string
  url: string
  source_type: 'webpage' | 'manual' | 'rss'
  enabled: boolean
  auth_note: string
  fetch_interval_minutes: number
  hash_pattern: string
  title_cleanup_rules: string
}

export interface BackupExportResponse {
  message: string
  exported_at: string
  settings: BackupSettings
  sources: BackupSource[]
}

export interface BackupImportRequest {
  settings?: BackupSettings | null
  sources?: BackupSource[]
}

export interface BackupImportResponse {
  message: string
}

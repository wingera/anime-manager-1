export interface AppSettings {
  id: number
  tmdb_language: string
  tmdb_region: string
  has_tmdb_api_key: boolean
  qbittorrent_url: string | null
  qbittorrent_username: string | null
  has_qbittorrent_password: boolean
  download_provider: 'qbittorrent' | 'nas115'
  cloud115_enabled: boolean
  cloud115_service_url: string | null
  has_cloud115_service_token: boolean
  download_dir: string
  media_library_dir: string
  matching_threshold: number
  tmdb_include_adult: boolean
  created_at: string
  updated_at: string
}

export interface SettingsUpdateRequest {
  tmdb_api_key?: string | null
  tmdb_language?: string | null
  tmdb_region?: string | null
  qbittorrent_url?: string | null
  qbittorrent_username?: string | null
  qbittorrent_password?: string | null
  download_provider?: 'qbittorrent' | 'nas115' | null
  cloud115_enabled?: boolean | null
  cloud115_service_url?: string | null
  cloud115_service_token?: string | null
  download_dir?: string | null
  media_library_dir?: string | null
  matching_threshold?: number | null
  tmdb_include_adult?: boolean | null
}

export interface ConnectionTestResponse {
  success: boolean
  message: string
}

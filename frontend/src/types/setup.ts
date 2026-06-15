export interface SetupStatusResponse {
  message: string
  installed: boolean
  missing_items: string[]
}

export interface SetupCompleteRequest {
  tmdb_api_key: string
  tmdb_language?: string
  tmdb_region?: string
  qbittorrent_url: string
  qbittorrent_username: string
  qbittorrent_password: string
  download_dir: string
  media_library_dir: string
  matching_threshold: number
}

export interface SetupCompleteResponse {
  message: string
}

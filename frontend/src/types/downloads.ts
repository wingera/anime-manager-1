export interface DownloadTask {
  id: number
  source_item_id: number
  source_title: string
  qbittorrent_hash: string | null
  magnet_uri: string
  save_path: string
  status: string
  progress: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface DownloadTaskMessageResponse {
  message: string
  download: DownloadTask
}

export interface DownloadTaskListResponse {
  message: string
  downloads: DownloadTask[]
}

export interface DownloadTaskDeleteResponse {
  message: string
}

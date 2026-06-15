export type DownloadFileType = 'video' | 'subtitle' | 'image' | 'sample' | 'document' | 'other' | 'unknown'

export interface DownloadFile {
  id: number
  download_task_id: number
  file_index: number
  provider_file_id: string | null
  parent_id: string | null
  name: string
  size: number
  progress: number
  priority: number
  file_type: DownloadFileType
  selected: boolean
  analysis_score: number
  season_number: number | null
  episode_number: number | null
  created_at: string
  updated_at: string
}

export interface RenamePreview {
  id: number
  download_file_id: number
  task_id: number | null
  file_id: string | null
  parent_id: string | null
  original_name: string
  target_name: string
  original_path: string
  target_path: string
  file_size: number
  file_type: DownloadFileType
  episode_number: number | null
  confidence: number
  conflict: boolean
  warning_message: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface DownloadFileListResponse {
  message: string
  files: DownloadFile[]
}

export interface DownloadFileMessageResponse {
  message: string
  file: DownloadFile
}

export interface DownloadFileUpdateRequest {
  selected?: boolean
  file_type?: DownloadFileType
  season_number?: number | null
  episode_number?: number | null
}

export interface FileAnalysisMessageResponse {
  message: string
  files: DownloadFile[]
}

export interface RenamePreviewListResponse {
  message: string
  previews: RenamePreview[]
}

export interface SimpleMessageResponse {
  message: string
}

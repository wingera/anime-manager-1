export type ImportJobStatus = 'pending' | 'completed' | 'failed' | 'rolled_back'
export type ImportMode = 'hardlink' | 'copy'
export type ImportActionStatus = 'pending' | 'completed' | 'failed' | 'rolled_back'
export type ImportActionType = 'hardlink' | 'copy'

export interface ImportJob {
  id: number
  download_task_id: number
  status: ImportJobStatus
  mode: ImportMode
  total_files: number
  completed_files: number
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface ImportFileAction {
  id: number
  import_job_id: number
  download_file_id: number
  source_path: string
  target_path: string
  action_type: ImportActionType
  status: ImportActionStatus
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface ImportJobListResponse {
  message: string
  imports: ImportJob[]
}

export interface ImportJobMessageResponse {
  message: string
  import_job: ImportJob
}

export interface ImportJobDetailResponse {
  message: string
  import_job: ImportJob
  actions: ImportFileAction[]
}

export interface ImportSimpleMessageResponse {
  message: string
}

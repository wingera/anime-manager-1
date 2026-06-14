export type OperationLogLevel = 'info' | 'warning' | 'error'

export interface OperationLog {
  id: number
  level: OperationLogLevel
  module: string
  message: string
  detail: string | null
  created_at: string
}

export interface OperationLogListResponse {
  message: string
  logs: OperationLog[]
}

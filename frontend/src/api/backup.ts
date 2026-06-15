import type { BackupExportResponse, BackupImportRequest, BackupImportResponse } from '../types/backup'

const API_BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {})
    },
    ...options
  })

  if (!response.ok) {
    let message = '请求失败，请稍后重试'
    try {
      const data = (await response.json()) as { message?: string; detail?: string }
      message = data.message ?? data.detail ?? message
    } catch {
      message = '请求失败，请检查后端服务是否正常'
    }
    throw new Error(message)
  }

  return (await response.json()) as T
}

export function exportBackup(): Promise<BackupExportResponse> {
  return request<BackupExportResponse>('/backup/export')
}

export function importBackup(payload: BackupImportRequest): Promise<BackupImportResponse> {
  return request<BackupImportResponse>('/backup/import', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

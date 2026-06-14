import type {
  ImportJobDetailResponse,
  ImportJobListResponse,
  ImportJobMessageResponse,
  ImportSimpleMessageResponse
} from '../types/imports'

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

export function getImports(): Promise<ImportJobListResponse> {
  return request<ImportJobListResponse>('/imports')
}

export function executeDownloadImport(downloadId: number): Promise<ImportJobMessageResponse> {
  return request<ImportJobMessageResponse>(`/downloads/${downloadId}/import`, {
    method: 'POST'
  })
}

export function getImportDetail(importId: number): Promise<ImportJobDetailResponse> {
  return request<ImportJobDetailResponse>(`/imports/${importId}`)
}

export function rollbackImport(importId: number): Promise<ImportSimpleMessageResponse> {
  return request<ImportSimpleMessageResponse>(`/imports/${importId}/rollback`, {
    method: 'POST'
  })
}

import type {
  DownloadTaskDeleteResponse,
  DownloadTaskListResponse,
  DownloadTaskMessageResponse
} from '../types/downloads'

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

export function getDownloads(): Promise<DownloadTaskListResponse> {
  return request<DownloadTaskListResponse>('/downloads')
}

export function createDownloadTask(itemId: number): Promise<DownloadTaskMessageResponse> {
  return request<DownloadTaskMessageResponse>(`/source-items/${itemId}/download`, {
    method: 'POST'
  })
}

export function refreshDownloadTask(downloadId: number): Promise<DownloadTaskMessageResponse> {
  return request<DownloadTaskMessageResponse>(`/downloads/${downloadId}/refresh`, {
    method: 'POST'
  })
}

export function deleteDownloadTask(downloadId: number): Promise<DownloadTaskDeleteResponse> {
  return request<DownloadTaskDeleteResponse>(`/downloads/${downloadId}`, {
    method: 'DELETE'
  })
}

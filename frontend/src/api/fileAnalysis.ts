import type {
  DownloadFileListResponse,
  DownloadFileMessageResponse,
  DownloadFileUpdateRequest,
  FileAnalysisMessageResponse,
  RenamePreviewListResponse,
  SimpleMessageResponse
} from '../types/fileAnalysis'

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

export function getDownloadFiles(downloadId: number): Promise<DownloadFileListResponse> {
  return request<DownloadFileListResponse>(`/downloads/${downloadId}/files`)
}

export function analyzeDownloadFiles(downloadId: number): Promise<FileAnalysisMessageResponse> {
  return request<FileAnalysisMessageResponse>(`/downloads/${downloadId}/files/analyze`, {
    method: 'POST'
  })
}

export function updateDownloadFile(
  fileId: number,
  payload: DownloadFileUpdateRequest
): Promise<DownloadFileMessageResponse> {
  return request<DownloadFileMessageResponse>(`/download-files/${fileId}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function applyDownloadFilePriority(downloadId: number): Promise<SimpleMessageResponse> {
  return request<SimpleMessageResponse>(`/downloads/${downloadId}/files/apply-priority`, {
    method: 'POST'
  })
}

export function getRenamePreview(downloadId: number): Promise<RenamePreviewListResponse> {
  return request<RenamePreviewListResponse>(`/downloads/${downloadId}/rename-preview`)
}

export function generateRenamePreview(downloadId: number): Promise<RenamePreviewListResponse> {
  return request<RenamePreviewListResponse>(`/downloads/${downloadId}/rename-preview`, {
    method: 'POST'
  })
}

import type {
  DeleteSourceResponse,
  SourceDetailScanRequest,
  SourceDetailScanResponse,
  SourceFormPayload,
  SourceItemImportRequest,
  SourceItemImportResponse,
  SourceItemListResponse,
  SourceListResponse,
  SourceMessageResponse,
  SourceTestRequest,
  SourceTestResponse,
  SourceUpdatePayload
} from '../types/sources'

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

export function getSources(): Promise<SourceListResponse> {
  return request<SourceListResponse>('/sources')
}

export function createSource(payload: SourceFormPayload): Promise<SourceMessageResponse> {
  return request<SourceMessageResponse>('/sources', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function updateSource(
  sourceId: number,
  payload: SourceUpdatePayload
): Promise<SourceMessageResponse> {
  return request<SourceMessageResponse>(`/sources/${sourceId}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function deleteSource(sourceId: number): Promise<DeleteSourceResponse> {
  return request<DeleteSourceResponse>(`/sources/${sourceId}`, {
    method: 'DELETE'
  })
}

export function testSource(
  sourceId: number,
  payload: SourceTestRequest = { page_number: 1 }
): Promise<SourceTestResponse> {
  return request<SourceTestResponse>(`/sources/${sourceId}/test`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function testSourceDetail(
  sourceId: number,
  payload: SourceDetailScanRequest
): Promise<SourceDetailScanResponse> {
  return request<SourceDetailScanResponse>(`/sources/${sourceId}/details/test`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function getSourceItems(): Promise<SourceItemListResponse> {
  return request<SourceItemListResponse>('/source-items')
}

export function importSourceItems(
  sourceId: number,
  payload: SourceItemImportRequest
): Promise<SourceItemImportResponse> {
  return request<SourceItemImportResponse>(`/sources/${sourceId}/items`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

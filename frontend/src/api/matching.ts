import type {
  MediaMatchListResponse,
  MediaMatchMessageResponse,
  MediaMatchPayload,
  TmdbSearchResponse
} from '../types/matching'

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

export function searchTmdb(itemId: number): Promise<TmdbSearchResponse> {
  return request<TmdbSearchResponse>(`/source-items/${itemId}/tmdb/search`, {
    method: 'POST'
  })
}

export function saveMatch(
  itemId: number,
  payload: MediaMatchPayload
): Promise<MediaMatchMessageResponse> {
  return request<MediaMatchMessageResponse>(`/source-items/${itemId}/match`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function getMatches(): Promise<MediaMatchListResponse> {
  return request<MediaMatchListResponse>('/matches')
}

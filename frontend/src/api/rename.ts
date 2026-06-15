import type { RenamePreviewListResponse } from '../types/fileAnalysis'
import type {
  AutoRenameResponse,
  RenameActionListResponse,
  RenameRuleMessageResponse,
  RenameRuleUpdateRequest
} from '../types/rename'

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

export function getRenameRule(): Promise<RenameRuleMessageResponse> {
  return request<RenameRuleMessageResponse>('/rename/rule')
}

export function saveRenameRule(
  payload: RenameRuleUpdateRequest
): Promise<RenameRuleMessageResponse> {
  return request<RenameRuleMessageResponse>('/rename/rule', {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export function getTaskRenamePreview(taskId: number): Promise<RenamePreviewListResponse> {
  return request<RenamePreviewListResponse>(`/tasks/${taskId}/rename-preview`)
}

export function generateTaskRenamePreview(taskId: number): Promise<RenamePreviewListResponse> {
  return request<RenamePreviewListResponse>(`/tasks/${taskId}/rename-preview`, {
    method: 'POST'
  })
}

export function applyTaskRename(taskId: number): Promise<RenameActionListResponse> {
  return request<RenameActionListResponse>(`/tasks/${taskId}/rename-apply`, {
    method: 'POST'
  })
}

export function getTaskRenameActions(taskId: number): Promise<RenameActionListResponse> {
  return request<RenameActionListResponse>(`/tasks/${taskId}/rename-actions`)
}

export function rollbackRenameAction(actionId: number): Promise<RenameActionListResponse> {
  return request<RenameActionListResponse>(`/rename-actions/${actionId}/rollback`, {
    method: 'POST'
  })
}

export function runTaskAutoRename(taskId: number): Promise<AutoRenameResponse> {
  return request<AutoRenameResponse>(`/tasks/${taskId}/auto-rename`, {
    method: 'POST'
  })
}

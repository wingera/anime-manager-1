import type { RenamePreview } from './fileAnalysis'

export interface RenameRule {
  id: number
  enabled: boolean
  auto_execute: boolean
  name_template: string
  episode_padding: number
  remove_words: string
  created_at: string
  updated_at: string
}

export interface RenameRuleUpdateRequest {
  enabled?: boolean
  auto_execute?: boolean
  name_template?: string
  episode_padding?: number
  remove_words?: string
}

export interface RenameRuleMessageResponse {
  message: string
  rule: RenameRule
}

export interface RenameAction {
  id: number
  preview_id: number
  task_id: number
  file_id: string
  old_name: string
  new_name: string
  old_parent_id: string | null
  new_parent_id: string | null
  action_type: string
  status: string
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface RenameActionListResponse {
  message: string
  actions: RenameAction[]
}

export interface AutoRenameResponse {
  message: string
  previews: RenamePreview[]
  actions: RenameAction[]
  skipped_reasons: string[]
}

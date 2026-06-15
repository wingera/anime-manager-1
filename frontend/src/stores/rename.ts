import { defineStore } from 'pinia'
import {
  applyTaskRename,
  generateTaskRenamePreview,
  getRenameRule,
  getTaskRenameActions,
  getTaskRenamePreview,
  rollbackRenameAction,
  runTaskAutoRename,
  saveRenameRule
} from '../api/rename'
import type { RenamePreview } from '../types/fileAnalysis'
import type { RenameAction, RenameRule, RenameRuleUpdateRequest } from '../types/rename'

interface RenameState {
  rule: RenameRule | null
  previews: RenamePreview[]
  actions: RenameAction[]
  loading: boolean
  saving: boolean
  generating: boolean
  applying: boolean
  rollingBackId: number | null
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useRenameStore = defineStore('rename', {
  state: (): RenameState => ({
    rule: null,
    previews: [],
    actions: [],
    loading: false,
    saving: false,
    generating: false,
    applying: false,
    rollingBackId: null,
    errorMessage: ''
  }),
  actions: {
    async fetchRule(): Promise<RenameRule> {
      this.loading = true
      this.errorMessage = ''
      try {
        const response = await getRenameRule()
        this.rule = response.rule
        return response.rule
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async saveRule(payload: RenameRuleUpdateRequest): Promise<RenameRule> {
      this.saving = true
      this.errorMessage = ''
      try {
        const response = await saveRenameRule(payload)
        this.rule = response.rule
        return response.rule
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.saving = false
      }
    },
    async fetchTask(taskId: number): Promise<void> {
      this.loading = true
      this.errorMessage = ''
      try {
        const [previewResponse, actionResponse] = await Promise.all([
          getTaskRenamePreview(taskId),
          getTaskRenameActions(taskId)
        ])
        this.previews = previewResponse.previews
        this.actions = actionResponse.actions
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async generatePreviews(taskId: number): Promise<RenamePreview[]> {
      this.generating = true
      this.errorMessage = ''
      try {
        const response = await generateTaskRenamePreview(taskId)
        this.previews = response.previews
        return this.previews
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.generating = false
      }
    },
    async applyRename(taskId: number): Promise<RenameAction[]> {
      this.applying = true
      this.errorMessage = ''
      try {
        const response = await applyTaskRename(taskId)
        this.actions = response.actions
        await this.fetchTask(taskId)
        return response.actions
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.applying = false
      }
    },
    async runAutoRename(taskId: number): Promise<void> {
      this.applying = true
      this.errorMessage = ''
      try {
        const response = await runTaskAutoRename(taskId)
        this.previews = response.previews
        this.actions = response.actions
        await this.fetchTask(taskId)
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.applying = false
      }
    },
    async rollback(actionId: number, taskId: number): Promise<void> {
      this.rollingBackId = actionId
      this.errorMessage = ''
      try {
        await rollbackRenameAction(actionId)
        await this.fetchTask(taskId)
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.rollingBackId = null
      }
    }
  }
})

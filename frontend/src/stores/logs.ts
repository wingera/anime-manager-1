import { defineStore } from 'pinia'
import { getOperationLogs } from '../api/logs'
import type { OperationLog } from '../types/logs'

interface LogsState {
  logs: OperationLog[]
  selectedModule: string
  loading: boolean
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useLogsStore = defineStore('logs', {
  state: (): LogsState => ({
    logs: [],
    selectedModule: '',
    loading: false,
    errorMessage: ''
  }),
  actions: {
    async fetchLogs(module?: string): Promise<OperationLog[]> {
      const targetModule = module ?? this.selectedModule
      this.loading = true
      this.errorMessage = ''
      this.selectedModule = targetModule
      try {
        const response = await getOperationLogs(targetModule || undefined)
        this.logs = response.logs
        return this.logs
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})

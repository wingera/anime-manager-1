import { defineStore } from 'pinia'
import { getDashboardSummary } from '../api/dashboard'
import type { DashboardSummary } from '../types/dashboard'

interface DashboardState {
  summary: DashboardSummary | null
  loading: boolean
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useDashboardStore = defineStore('dashboard', {
  state: (): DashboardState => ({
    summary: null,
    loading: false,
    errorMessage: ''
  }),
  actions: {
    async fetchSummary(): Promise<DashboardSummary> {
      this.loading = true
      this.errorMessage = ''
      try {
        const response = await getDashboardSummary()
        this.summary = response.summary
        return this.summary
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})

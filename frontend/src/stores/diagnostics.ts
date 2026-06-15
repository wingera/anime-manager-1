import { defineStore } from 'pinia'
import { getDiagnostics } from '../api/diagnostics'
import type { DiagnosticCheck } from '../types/diagnostics'

interface DiagnosticsState {
  checks: DiagnosticCheck[]
  loading: boolean
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useDiagnosticsStore = defineStore('diagnostics', {
  state: (): DiagnosticsState => ({
    checks: [],
    loading: false,
    errorMessage: ''
  }),
  actions: {
    async fetchDiagnostics(): Promise<void> {
      this.loading = true
      this.errorMessage = ''
      try {
        const response = await getDiagnostics()
        this.checks = response.checks
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    }
  }
})

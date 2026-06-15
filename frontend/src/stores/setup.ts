import { defineStore } from 'pinia'
import { completeSetup, getSetupStatus } from '../api/setup'
import type { SetupCompleteRequest, SetupStatusResponse } from '../types/setup'

interface SetupState {
  status: SetupStatusResponse | null
  loading: boolean
  saving: boolean
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useSetupStore = defineStore('setup', {
  state: (): SetupState => ({
    status: null,
    loading: false,
    saving: false,
    errorMessage: ''
  }),
  actions: {
    async fetchStatus(): Promise<SetupStatusResponse> {
      this.loading = true
      this.errorMessage = ''
      try {
        this.status = await getSetupStatus()
        return this.status
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async saveSetup(payload: SetupCompleteRequest): Promise<void> {
      this.saving = true
      this.errorMessage = ''
      try {
        await completeSetup(payload)
        await this.fetchStatus()
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.saving = false
      }
    }
  }
})

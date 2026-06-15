import { defineStore } from 'pinia'
import { exportBackup, importBackup } from '../api/backup'
import type { BackupExportResponse, BackupImportRequest } from '../types/backup'

interface BackupState {
  latestBackup: BackupExportResponse | null
  loading: boolean
  importing: boolean
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useBackupStore = defineStore('backup', {
  state: (): BackupState => ({
    latestBackup: null,
    loading: false,
    importing: false,
    errorMessage: ''
  }),
  actions: {
    async exportConfig(): Promise<BackupExportResponse> {
      this.loading = true
      this.errorMessage = ''
      try {
        this.latestBackup = await exportBackup()
        return this.latestBackup
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async importConfig(payload: BackupImportRequest): Promise<void> {
      this.importing = true
      this.errorMessage = ''
      try {
        await importBackup(payload)
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.importing = false
      }
    }
  }
})

import { defineStore } from 'pinia'
import {
  executeDownloadImport,
  getImportDetail,
  getImports,
  rollbackImport
} from '../api/imports'
import type { ImportFileAction, ImportJob } from '../types/imports'

interface ImportsState {
  imports: ImportJob[]
  currentJob: ImportJob | null
  actions: ImportFileAction[]
  loading: boolean
  detailLoading: boolean
  executing: boolean
  rollingBackId: number | null
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useImportsStore = defineStore('imports', {
  state: (): ImportsState => ({
    imports: [],
    currentJob: null,
    actions: [],
    loading: false,
    detailLoading: false,
    executing: false,
    rollingBackId: null,
    errorMessage: ''
  }),
  actions: {
    async fetchImports(): Promise<ImportJob[]> {
      this.loading = true
      this.errorMessage = ''
      try {
        const response = await getImports()
        this.imports = response.imports
        return this.imports
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async executeForDownload(downloadId: number): Promise<ImportJob> {
      this.executing = true
      this.errorMessage = ''
      try {
        const response = await executeDownloadImport(downloadId)
        await this.fetchImports()
        return response.import_job
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.executing = false
      }
    },
    async fetchDetail(importId: number): Promise<ImportFileAction[]> {
      this.detailLoading = true
      this.errorMessage = ''
      try {
        const response = await getImportDetail(importId)
        this.currentJob = response.import_job
        this.actions = response.actions
        return this.actions
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.detailLoading = false
      }
    },
    async rollback(importId: number): Promise<void> {
      this.rollingBackId = importId
      this.errorMessage = ''
      try {
        await rollbackImport(importId)
        await this.fetchImports()
        await this.fetchDetail(importId)
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.rollingBackId = null
      }
    }
  }
})

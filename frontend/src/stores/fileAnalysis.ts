import { defineStore } from 'pinia'
import {
  analyzeDownloadFiles,
  applyDownloadFilePriority,
  generateRenamePreview,
  getDownloadFiles,
  getRenamePreview,
  updateDownloadFile
} from '../api/fileAnalysis'
import type { DownloadFile, DownloadFileUpdateRequest, RenamePreview } from '../types/fileAnalysis'

interface FileAnalysisState {
  files: DownloadFile[]
  previews: RenamePreview[]
  loading: boolean
  analyzing: boolean
  applying: boolean
  generating: boolean
  savingFileId: number | null
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useFileAnalysisStore = defineStore('fileAnalysis', {
  state: (): FileAnalysisState => ({
    files: [],
    previews: [],
    loading: false,
    analyzing: false,
    applying: false,
    generating: false,
    savingFileId: null,
    errorMessage: ''
  }),
  actions: {
    async fetchFiles(downloadId: number): Promise<DownloadFile[]> {
      this.loading = true
      this.errorMessage = ''
      try {
        const response = await getDownloadFiles(downloadId)
        this.files = response.files
        return this.files
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async analyzeFiles(downloadId: number): Promise<DownloadFile[]> {
      this.analyzing = true
      this.errorMessage = ''
      try {
        const response = await analyzeDownloadFiles(downloadId)
        this.files = response.files
        return this.files
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.analyzing = false
      }
    },
    async saveFile(fileId: number, payload: DownloadFileUpdateRequest): Promise<DownloadFile> {
      this.savingFileId = fileId
      this.errorMessage = ''
      try {
        const response = await updateDownloadFile(fileId, payload)
        const index = this.files.findIndex((file) => file.id === fileId)
        if (index >= 0) this.files[index] = response.file
        return response.file
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.savingFileId = null
      }
    },
    async applyPriority(downloadId: number): Promise<void> {
      this.applying = true
      this.errorMessage = ''
      try {
        await applyDownloadFilePriority(downloadId)
        await this.fetchFiles(downloadId)
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.applying = false
      }
    },
    async fetchPreviews(downloadId: number): Promise<RenamePreview[]> {
      this.loading = true
      this.errorMessage = ''
      try {
        const response = await getRenamePreview(downloadId)
        this.previews = response.previews
        return this.previews
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async generatePreviews(downloadId: number): Promise<RenamePreview[]> {
      this.generating = true
      this.errorMessage = ''
      try {
        const response = await generateRenamePreview(downloadId)
        this.previews = response.previews
        return this.previews
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.generating = false
      }
    }
  }
})

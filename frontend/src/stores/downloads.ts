import { defineStore } from 'pinia'
import {
  createDownloadTask,
  deleteDownloadTask,
  getDownloads,
  refreshDownloadTask
} from '../api/downloads'
import type { DownloadTask } from '../types/downloads'

interface DownloadsState {
  downloads: DownloadTask[]
  loading: boolean
  creatingItemId: number | null
  refreshingId: number | null
  deletingId: number | null
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useDownloadsStore = defineStore('downloads', {
  state: (): DownloadsState => ({
    downloads: [],
    loading: false,
    creatingItemId: null,
    refreshingId: null,
    deletingId: null,
    errorMessage: ''
  }),
  actions: {
    async fetchDownloads(): Promise<DownloadTask[]> {
      this.loading = true
      this.errorMessage = ''
      try {
        const response = await getDownloads()
        this.downloads = response.downloads
        return this.downloads
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async createForSourceItem(itemId: number): Promise<DownloadTask> {
      this.creatingItemId = itemId
      this.errorMessage = ''
      try {
        const response = await createDownloadTask(itemId)
        await this.fetchDownloads()
        return response.download
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.creatingItemId = null
      }
    },
    async refreshDownload(downloadId: number): Promise<DownloadTask> {
      this.refreshingId = downloadId
      this.errorMessage = ''
      try {
        const response = await refreshDownloadTask(downloadId)
        await this.fetchDownloads()
        return response.download
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.refreshingId = null
      }
    },
    async removeDownload(downloadId: number): Promise<void> {
      this.deletingId = downloadId
      this.errorMessage = ''
      try {
        await deleteDownloadTask(downloadId)
        await this.fetchDownloads()
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.deletingId = null
      }
    }
  }
})

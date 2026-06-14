import { defineStore } from 'pinia'
import {
  createSource,
  deleteSource,
  getSourceItems,
  getSources,
  importSourceItems,
  testSource,
  updateSource
} from '../api/sources'
import type {
  SourceItemImportResponse,
  SourceFormPayload,
  SourceItem,
  SourcePreviewItem,
  SourceSite,
  SourceTestResponse,
  SourceUpdatePayload
} from '../types/sources'

interface SourcesState {
  sources: SourceSite[]
  sourceItems: SourceItem[]
  previewItems: SourcePreviewItem[]
  previewSourceId: number | null
  previewFoundCount: number
  loading: boolean
  saving: boolean
  testing: boolean
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useSourcesStore = defineStore('sources', {
  state: (): SourcesState => ({
    sources: [],
    sourceItems: [],
    previewItems: [],
    previewSourceId: null,
    previewFoundCount: 0,
    loading: false,
    saving: false,
    testing: false,
    errorMessage: ''
  }),
  actions: {
    async fetchSources(): Promise<SourceSite[]> {
      this.loading = true
      this.errorMessage = ''
      try {
        const response = await getSources()
        this.sources = response.sources
        return this.sources
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async saveSource(
      payload: SourceFormPayload,
      sourceId?: number
    ): Promise<SourceSite> {
      this.saving = true
      this.errorMessage = ''
      try {
        const response =
          sourceId === undefined ? await createSource(payload) : await updateSource(sourceId, payload)
        await this.fetchSources()
        return response.source
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.saving = false
      }
    },
    async updateSource(sourceId: number, payload: SourceUpdatePayload): Promise<SourceSite> {
      this.saving = true
      this.errorMessage = ''
      try {
        const response = await updateSource(sourceId, payload)
        await this.fetchSources()
        return response.source
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.saving = false
      }
    },
    async removeSource(sourceId: number): Promise<void> {
      this.saving = true
      this.errorMessage = ''
      try {
        await deleteSource(sourceId)
        await this.fetchSources()
        if (this.previewSourceId === sourceId) {
          this.previewSourceId = null
          this.previewFoundCount = 0
          this.previewItems = []
        }
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.saving = false
      }
    },
    async testSource(sourceId: number): Promise<SourceTestResponse> {
      this.testing = true
      this.errorMessage = ''
      try {
        const response = await testSource(sourceId)
        this.previewSourceId = response.source_id
        this.previewFoundCount = response.found_count
        this.previewItems = response.items
        return response
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.testing = false
      }
    },
    async fetchSourceItems(): Promise<SourceItem[]> {
      const response = await getSourceItems()
      this.sourceItems = response.items
      return this.sourceItems
    },
    async addPreviewItems(
      sourceId: number,
      items: SourcePreviewItem[]
    ): Promise<SourceItemImportResponse> {
      this.saving = true
      this.errorMessage = ''
      try {
        const response = await importSourceItems(sourceId, { items })
        await this.fetchSourceItems()
        return response
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.saving = false
      }
    }
  }
})

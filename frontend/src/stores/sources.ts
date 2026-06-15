import { defineStore } from 'pinia'
import {
  createSource,
  deleteSource,
  getSourceItems,
  getSources,
  importSourceItems,
  testSource,
  testSourceDetail,
  updateSource
} from '../api/sources'
import type {
  SourceDetailScanResponse,
  SourceItemImportResponse,
  SourceFormPayload,
  SourceItem,
  SourcePagination,
  SourcePreviewItem,
  SourceScanFailure,
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
  previewWarningMessage: string | null
  previewPagination: SourcePagination | null
  previewFailedPages: SourceScanFailure[]
  loading: boolean
  saving: boolean
  testing: boolean
  rescanningDetailUrl: string | null
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
    previewWarningMessage: null,
    previewPagination: null,
    previewFailedPages: [],
    loading: false,
    saving: false,
    testing: false,
    rescanningDetailUrl: null,
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
          this.previewWarningMessage = null
          this.previewPagination = null
          this.previewFailedPages = []
          this.previewItems = []
        }
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.saving = false
      }
    },
    async testSource(sourceId: number, pageNumber = 1): Promise<SourceTestResponse> {
      this.testing = true
      this.errorMessage = ''
      try {
        const response = await testSource(sourceId, { page_number: pageNumber })
        this.previewSourceId = response.source_id
        this.previewFoundCount = response.found_count
        this.previewWarningMessage = response.warning_message
        this.previewPagination = response.pagination
        this.previewFailedPages = response.failed_pages
        this.previewItems = response.items
        return response
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.testing = false
      }
    },
    async testFailedDetailPage(
      sourceId: number,
      page: SourceScanFailure,
      pageNumber = 1
    ): Promise<SourceDetailScanResponse> {
      this.rescanningDetailUrl = page.url
      this.errorMessage = ''
      try {
        const response = await testSourceDetail(sourceId, {
          url: page.url,
          title: page.title,
          page_number: pageNumber
        })
        const existingHashes = new Set(this.previewItems.map((item) => item.info_hash))
        const newItems = response.items.filter((item) => !existingHashes.has(item.info_hash))
        if (newItems.length > 0) {
          this.previewItems = [...this.previewItems, ...newItems]
          this.previewFoundCount += newItems.length
        }
        if (response.failed_page === null) {
          this.previewFailedPages = this.previewFailedPages.filter((item) => item.url !== page.url)
        } else {
          this.previewFailedPages = this.previewFailedPages.map((item) =>
            item.url === page.url ? response.failed_page as SourceScanFailure : item
          )
        }
        return response
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.rescanningDetailUrl = null
      }
    },
    async fetchSourceItems(): Promise<SourceItem[]> {
      const response = await getSourceItems()
      this.sourceItems = response.items
      return this.sourceItems
    },
    async addPreviewItems(
      sourceId: number,
      items: SourcePreviewItem[],
      permissionConfirmed: boolean
    ): Promise<SourceItemImportResponse> {
      this.saving = true
      this.errorMessage = ''
      try {
        const response = await importSourceItems(sourceId, {
          items,
          permission_confirmed: permissionConfirmed
        })
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

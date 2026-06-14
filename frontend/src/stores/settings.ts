import { defineStore } from 'pinia'
import {
  getSettings,
  testQbittorrent as requestQbittorrentTest,
  testTmdb as requestTmdbTest,
  updateSettings
} from '../api/settings'
import type { AppSettings, ConnectionTestResponse, SettingsUpdateRequest } from '../types/settings'

interface SettingsState {
  settings: AppSettings | null
  loading: boolean
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useSettingsStore = defineStore('settings', {
  state: (): SettingsState => ({
    settings: null,
    loading: false,
    errorMessage: ''
  }),
  actions: {
    async fetchSettings(): Promise<AppSettings> {
      this.loading = true
      this.errorMessage = ''
      try {
        this.settings = await getSettings()
        return this.settings
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async saveSettings(payload: SettingsUpdateRequest): Promise<AppSettings> {
      this.loading = true
      this.errorMessage = ''
      try {
        this.settings = await updateSettings(payload)
        return this.settings
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async testTmdb(): Promise<ConnectionTestResponse> {
      this.errorMessage = ''
      try {
        return await requestTmdbTest()
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      }
    },
    async testQbittorrent(): Promise<ConnectionTestResponse> {
      this.errorMessage = ''
      try {
        return await requestQbittorrentTest()
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      }
    }
  }
})

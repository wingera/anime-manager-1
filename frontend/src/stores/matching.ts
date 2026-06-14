import { defineStore } from 'pinia'
import { getMatches, saveMatch, searchTmdb } from '../api/matching'
import type {
  MediaMatch,
  MediaMatchPayload,
  TmdbCandidate,
  TmdbSearchResponse
} from '../types/matching'

interface MatchingState {
  matches: MediaMatch[]
  candidatesByItemId: Record<number, TmdbCandidate[]>
  loading: boolean
  searchingItemId: number | null
  saving: boolean
  errorMessage: string
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '操作失败，请稍后重试'
}

export const useMatchingStore = defineStore('matching', {
  state: (): MatchingState => ({
    matches: [],
    candidatesByItemId: {},
    loading: false,
    searchingItemId: null,
    saving: false,
    errorMessage: ''
  }),
  actions: {
    async fetchMatches(): Promise<MediaMatch[]> {
      this.loading = true
      this.errorMessage = ''
      try {
        const response = await getMatches()
        this.matches = response.matches
        return this.matches
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.loading = false
      }
    },
    async searchCandidates(itemId: number): Promise<TmdbSearchResponse> {
      this.searchingItemId = itemId
      this.errorMessage = ''
      try {
        const response = await searchTmdb(itemId)
        this.candidatesByItemId[itemId] = response.candidates
        return response
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.searchingItemId = null
      }
    },
    async saveItemMatch(itemId: number, payload: MediaMatchPayload): Promise<MediaMatch> {
      this.saving = true
      this.errorMessage = ''
      try {
        const response = await saveMatch(itemId, payload)
        await this.fetchMatches()
        return response.match
      } catch (error) {
        this.errorMessage = getErrorMessage(error)
        throw error
      } finally {
        this.saving = false
      }
    }
  }
})

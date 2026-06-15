export interface TmdbCandidate {
  tmdb_id: number
  title: string
  original_title: string | null
  first_air_date: string | null
  overview: string
  poster_path: string | null
  match_score: number
  search_query: string
}

export interface TmdbSearchResponse {
  message: string
  search_queries: string[]
  candidates: TmdbCandidate[]
}

export interface MediaMatchPayload {
  tmdb_id: number | null
  title: string | null
  original_title: string | null
  year: number | null
  season_number: number | null
  episode_number: number | null
  episode_title: string | null
  match_score: number
  status: string
}

export interface MediaMatch {
  id: number
  source_item_id: number
  tmdb_id: number | null
  title: string | null
  original_title: string | null
  year: number | null
  season_number: number | null
  episode_number: number | null
  episode_title: string | null
  match_score: number
  status: string
  created_at: string
  updated_at: string
}

export interface MediaMatchMessageResponse {
  message: string
  match: MediaMatch
}

export interface MediaMatchListResponse {
  message: string
  matches: MediaMatch[]
}

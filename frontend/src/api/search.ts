import { get } from './index'
import type { PaginatedResponse } from './documents'

export interface SearchResult {
  id: number
  type: string
  title: string
  description: string | null
  highlight: string | null
  url: string | null
  extra: Record<string, any> | null
}

export const searchApi = {
  search: (params: Record<string, any>, config?: Record<string, any>) =>
    get<PaginatedResponse<SearchResult>>('/search', params, config),
}

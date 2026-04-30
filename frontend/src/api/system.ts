import { get, put, post, del } from './index'

export interface AIConfigItem {
  key: string
  value: string
  description: string | null
}

export interface AIProvider {
  id: number
  name: string
  provider_type: string
  api_base: string
  api_key: string
  model: string
  max_tokens: number
  temperature: number
  is_enabled: boolean
  sort_order: number
  created_at: string | null
  updated_at: string | null
}

export interface ProviderCreate {
  name: string
  provider_type?: string
  api_base: string
  api_key?: string
  model: string
  max_tokens?: number
  temperature?: number
  is_enabled?: boolean
  sort_order?: number
}

export interface ProviderUpdate {
  name?: string
  provider_type?: string
  api_base?: string
  api_key?: string
  model?: string
  max_tokens?: number
  temperature?: number
  is_enabled?: boolean
  sort_order?: number
}

export const systemApi = {
  // RAG config
  getAIConfig: () => get<{ items: AIConfigItem[] }>('/system/ai-config'),
  updateAIConfig: (items: AIConfigItem[]) =>
    put<{ detail: string; items: AIConfigItem[] }>('/system/ai-config', { items }),

  // Provider CRUD
  getProviders: () => get<AIProvider[]>('/system/ai-providers'),
  createProvider: (data: ProviderCreate) =>
    post<{ detail: string; id: number }>('/system/ai-providers', data),
  updateProvider: (id: number, data: ProviderUpdate) =>
    put<{ detail: string }>(`/system/ai-providers/${id}`, data),
  deleteProvider: (id: number) =>
    del<{ detail: string }>(`/system/ai-providers/${id}`),
}

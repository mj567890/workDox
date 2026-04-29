import { get, post, del } from './index'

export interface ChatRequest {
  query: string
  document_ids?: number[]
  conversation_id?: number
}

export interface ChatResponse {
  answer: string
  sources: Source[]
  conversation_id: number
}

export interface Source {
  document_id: number
  document_name: string
  chunk_index: number
  similarity: number
  text_snippet: string
}

export interface SummarizeResponse {
  document_id: number
  summary: string
}

export interface Conversation {
  id: number
  title: string
  document_id: number | null
  message_count: number
  created_at: string
  updated_at: string
}

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources: Source[] | null
  created_at: string
}

export const aiApi = {
  chat: (data: ChatRequest) => post<ChatResponse>('/ai/chat', data),
  summarize: (documentId: number) =>
    post<SummarizeResponse>('/ai/summarize', { document_id: documentId }),
  embedDocument: (documentId: number) =>
    post<{ document_id: number; chunks_created: number }>(
      `/ai/documents/${documentId}/embed`
    ),
  getConversations: () => get<Conversation[]>('/ai/conversations'),
  getConversationMessages: (id: number) =>
    get<Message[]>(`/ai/conversations/${id}`),
  deleteConversation: (id: number) => del(`/ai/conversations/${id}`),
}

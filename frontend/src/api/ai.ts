import { get, post, del } from './index'

export interface ChatRequest {
  query: string
  document_ids?: number[]
  conversation_id?: number
  provider_id?: number
}

export interface ChatResponse {
  answer: string
  sources: Source[]
  conversation_id: number
}

export interface StreamEvent {
  type: 'sources' | 'token' | 'done' | 'error'
  data?: Source[]
  content?: string
  conversation_id?: number
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

export interface ProviderOption {
  id: number
  name: string
  provider_type: string
  model: string
}

async function chatStreamImpl(
  data: ChatRequest,
  onEvent: (event: StreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem('token')
  const response = await fetch('/api/v1/ai/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
    signal,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
    throw new Error(err.detail || `请求失败 (${response.status})`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('浏览器不支持流式读取')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event: StreamEvent = JSON.parse(line.slice(6))
          onEvent(event)
        } catch {
          // skip malformed JSON lines
        }
      }
    }
  }

  // Process remaining buffer
  if (buffer.startsWith('data: ')) {
    try {
      const event: StreamEvent = JSON.parse(buffer.slice(6))
      onEvent(event)
    } catch {
      // skip
    }
  }
}

export const aiApi = {
  getProviders: () => get<ProviderOption[]>('/ai/providers'),
  chat: (data: ChatRequest) => post<ChatResponse>('/ai/chat', data),
  chatStream: chatStreamImpl,
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

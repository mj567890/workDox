import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  aiApi,
  type Conversation,
  type Message,
  type ChatResponse,
  type ProviderOption,
  type Source,
} from '@/api/ai'

export const useAIStore = defineStore('ai', () => {
  const conversations = ref<Conversation[]>([])
  const currentMessages = ref<Message[]>([])
  const currentConversationId = ref<number | null>(null)
  const loading = ref(false)
  const providers = ref<ProviderOption[]>([])
  const selectedProviderId = ref<number | null>(null)

  async function fetchConversations() {
    conversations.value = await aiApi.getConversations()
  }

  async function fetchProviders() {
    providers.value = await aiApi.getProviders()
  }

  async function fetchMessages(convId: number) {
    currentConversationId.value = convId
    currentMessages.value = await aiApi.getConversationMessages(convId)
  }

  async function sendMessage(
    query: string,
    documentIds?: number[]
  ): Promise<ChatResponse> {
    // Push user message immediately so the user sees their question
    const userMsg: Message = {
      id: Date.now(),
      role: 'user',
      content: query,
      sources: null,
      created_at: new Date().toISOString(),
    }
    // Show a thinking placeholder while waiting for the AI
    const placeholderId = Date.now() + 1
    const placeholder: Message = {
      id: placeholderId,
      role: 'assistant',
      content: '正在思考...',
      sources: null,
      created_at: new Date().toISOString(),
    }
    currentMessages.value.push(userMsg, placeholder)

    loading.value = true
    const controller = new AbortController()
    let fullAnswer = ''
    let sources: Source[] = []
    let conversationId: number | null = null

    try {
      await aiApi.chatStream(
        {
          query,
          document_ids: documentIds,
          conversation_id: currentConversationId.value ?? undefined,
          provider_id: selectedProviderId.value ?? undefined,
        },
        (event) => {
          if (event.type === 'sources' && event.data) {
            sources = event.data
            // Update placeholder with sources
            const idx = currentMessages.value.findIndex(m => m.id === placeholderId)
            if (idx >= 0) {
              currentMessages.value[idx] = {
                ...currentMessages.value[idx],
                sources: event.data,
              }
            }
          } else if (event.type === 'token') {
            fullAnswer += event.content || ''
            // Update placeholder content in real-time
            const idx = currentMessages.value.findIndex(m => m.id === placeholderId)
            if (idx >= 0) {
              currentMessages.value[idx] = {
                ...currentMessages.value[idx],
                content: fullAnswer || '正在思考...',
              }
            }
          } else if (event.type === 'done') {
            conversationId = event.conversation_id ?? null
          } else if (event.type === 'error') {
            throw new Error(event.content || '生成回答时出错')
          }
        },
        controller.signal,
      )

      // Finalize the message
      currentConversationId.value = conversationId
      const idx = currentMessages.value.findIndex(m => m.id === placeholderId)
      if (idx >= 0) {
        currentMessages.value[idx] = {
          id: Date.now() + 2,
          role: 'assistant',
          content: fullAnswer || '（无内容）',
          sources: sources,
          created_at: new Date().toISOString(),
        }
      }
      await fetchConversations()
      return {
        answer: fullAnswer,
        sources,
        conversation_id: conversationId ?? 0,
      }
    } catch (err: any) {
      controller.abort() // Cancel the fetch stream
      // Remove the placeholder on error
      const idx = currentMessages.value.findIndex(m => m.id === placeholderId)
      if (idx >= 0) {
        currentMessages.value[idx] = {
          id: placeholderId,
          role: 'assistant',
          content: err?.name === 'AbortError' ? '请求已取消' : '抱歉，请求失败，请重试。',
          sources: null,
          created_at: new Date().toISOString(),
        }
      }
      throw new Error()
    } finally {
      loading.value = false
    }
  }

  async function deleteConversation(id: number) {
    await aiApi.deleteConversation(id)
    if (currentConversationId.value === id) {
      currentConversationId.value = null
      currentMessages.value = []
    }
    await fetchConversations()
  }

  function newChat() {
    currentConversationId.value = null
    currentMessages.value = []
  }

  return {
    conversations,
    currentMessages,
    currentConversationId,
    loading,
    providers,
    selectedProviderId,
    fetchConversations,
    fetchProviders,
    fetchMessages,
    sendMessage,
    deleteConversation,
    newChat,
  }
})

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  aiApi,
  type Conversation,
  type Message,
  type ChatResponse,
  type ProviderOption,
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
    try {
      const response = await aiApi.chat({
        query,
        document_ids: documentIds,
        conversation_id: currentConversationId.value ?? undefined,
        provider_id: selectedProviderId.value ?? undefined,
      })
      currentConversationId.value = response.conversation_id
      // Replace placeholder with the actual answer
      const idx = currentMessages.value.findIndex(m => m.id === placeholderId)
      if (idx >= 0) {
        currentMessages.value[idx] = {
          id: Date.now() + 2,
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          created_at: new Date().toISOString(),
        }
      }
      await fetchConversations()
      return response
    } catch {
      // Remove the placeholder on error
      const idx = currentMessages.value.findIndex(m => m.id === placeholderId)
      if (idx >= 0) {
        currentMessages.value[idx] = {
          id: placeholderId,
          role: 'assistant',
          content: '抱歉，请求失败，请重试。',
          sources: null,
          created_at: new Date().toISOString(),
        }
      }
      throw new Error() // re-throw for component-level handling
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

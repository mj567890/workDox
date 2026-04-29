import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  aiApi,
  type Conversation,
  type Message,
  type ChatRequest,
  type ChatResponse,
} from '@/api/ai'

export const useAIStore = defineStore('ai', () => {
  const conversations = ref<Conversation[]>([])
  const currentMessages = ref<Message[]>([])
  const currentConversationId = ref<number | null>(null)
  const loading = ref(false)

  async function fetchConversations() {
    conversations.value = await aiApi.getConversations()
  }

  async function fetchMessages(convId: number) {
    currentConversationId.value = convId
    currentMessages.value = await aiApi.getConversationMessages(convId)
  }

  async function sendMessage(
    query: string,
    documentIds?: number[]
  ): Promise<ChatResponse> {
    loading.value = true
    try {
      const response = await aiApi.chat({
        query,
        document_ids: documentIds,
        conversation_id: currentConversationId.value ?? undefined,
      })
      currentConversationId.value = response.conversation_id
      currentMessages.value.push(
        {
          id: Date.now(),
          role: 'user',
          content: query,
          sources: null,
          created_at: new Date().toISOString(),
        },
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          created_at: new Date().toISOString(),
        }
      )
      await fetchConversations()
      return response
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
    fetchConversations,
    fetchMessages,
    sendMessage,
    deleteConversation,
    newChat,
  }
})

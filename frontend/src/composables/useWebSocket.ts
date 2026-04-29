import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 10
  const authStore = useAuthStore()

  function connect() {
    const token = localStorage.getItem('token')
    const user = authStore.user
    if (!token || !user) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${protocol}://${window.location.host}/api/v1/ws/${user.id}?token=${token}`

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      isConnected.value = true
      reconnectAttempts.value = 0
    }

    ws.value.onclose = () => {
      isConnected.value = false
      if (reconnectAttempts.value < maxReconnectAttempts) {
        const delay = Math.min(30000, 1000 * Math.pow(2, reconnectAttempts.value))
        reconnectAttempts.value++
        setTimeout(connect, delay)
      }
    }

    ws.value.onerror = () => {
      ws.value?.close()
    }
  }

  function disconnect() {
    ws.value?.close()
    ws.value = null
  }

  return { ws, isConnected, connect, disconnect }
}

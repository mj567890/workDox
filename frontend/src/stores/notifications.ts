import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notificationsApi, type NotificationItem } from '@/api/notifications'
import { useWebSocket } from '@/composables/useWebSocket'

let pollingTimer: ReturnType<typeof setInterval> | null = null

export const useNotificationStore = defineStore('notifications', () => {
  const notifications = ref<NotificationItem[]>([])
  const unreadCount = ref(0)
  const total = ref(0)
  const wsConnected = ref(false)
  const isPolling = ref(false)

  async function fetchNotifications(params?: Record<string, any>) {
    const res = await notificationsApi.getList(params)
    notifications.value = res.items
    total.value = res.total
    return res
  }

  async function fetchUnreadCount() {
    const res = await notificationsApi.getUnreadCount()
    unreadCount.value = res.unread_count
  }

  async function markAsRead(id: number) {
    await notificationsApi.markAsRead(id)
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    const notif = notifications.value.find(n => n.id === id)
    if (notif) notif.is_read = true
  }

  async function markAllAsRead() {
    await notificationsApi.markAllAsRead()
    unreadCount.value = 0
    notifications.value.forEach(n => (n.is_read = true))
  }

  function startPolling() {
    if (isPolling.value) return
    isPolling.value = true
    fetchUnreadCount()
    pollingTimer = setInterval(() => {
      fetchUnreadCount()
    }, 30000) // Poll every 30 seconds as fallback
  }

  function stopPolling() {
    if (pollingTimer) {
      clearInterval(pollingTimer)
      pollingTimer = null
    }
    isPolling.value = false
  }

  function initWebSocket() {
    const { connect, ws } = useWebSocket()
    connect()

    // Set up message handler for incoming WebSocket messages
    const setupHandler = () => {
      if (ws.value) {
        ws.value.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            if (msg.type === 'notification') {
              fetchUnreadCount()
            }
          } catch {
            // Ignore parse errors from non-JSON messages (e.g., ping/pong)
          }
        }
      }
    }

    // Attempt to set handler immediately after connect()
    setTimeout(() => {
      setupHandler()
    }, 100)

    // Fallback: if WebSocket not connected within 5 seconds, use polling
    setTimeout(() => {
      if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
        startPolling()
      } else {
        wsConnected.value = true
      }
    }, 5000)
  }

  return {
    notifications,
    unreadCount,
    total,
    wsConnected,
    isPolling,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    initWebSocket,
    startPolling,
    stopPolling,
  }
})

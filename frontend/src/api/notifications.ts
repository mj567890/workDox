import { get, put } from './index'
import type { PaginatedResponse } from './documents'

export interface NotificationItem {
  id: number
  user_id: number
  type: string
  title: string
  content: string | null
  is_read: boolean
  created_at: string
}

export const notificationsApi = {
  getList: (params?: Record<string, any>) => get<PaginatedResponse<NotificationItem>>('/notifications', params),
  getUnreadCount: () => get<{ unread_count: number }>('/notifications/unread-count'),
  markAsRead: (id: number) => put(`/notifications/${id}/read`),
  markAllAsRead: () => put('/notifications/read-all'),
}

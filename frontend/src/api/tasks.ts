import { get, post, put, del } from './index'
import type { PaginatedResponse } from './documents'

export interface TaskItem {
  id: number
  matter_id: number
  matter_title: string
  node_id: number | null
  node_name: string | null
  title: string
  assigner_id: number
  assigner_name: string
  assignee_id: number
  assignee_name: string
  status: string
  priority: string
  due_time: string | null
  description: string | null
  created_at: string
}

export const tasksApi = {
  getList: (params?: Record<string, any>) => get<PaginatedResponse<TaskItem>>('/tasks', params),
  create: (data: Record<string, any>) => post<TaskItem>('/tasks', data),
  getDetail: (id: number) => get<TaskItem>(`/tasks/${id}`),
  update: (id: number, data: Record<string, any>) => put<TaskItem>(`/tasks/${id}`, data),
  delete: (id: number) => del(`/tasks/${id}`),
}

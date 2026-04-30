import { get, post, put, del } from './index'

export interface SlotItem {
  id: number
  name: string
  description: string | null
  is_required: boolean
  status: string
  waive_reason: string | null
  maturity: string | null
  maturity_note: string | null
  document_id: number | null
  document_name: string | null
  version_count: number
}

export interface StageItem {
  id: number
  order: number
  name: string
  status: string
  notes: string | null
  slots: SlotItem[]
}

export interface BoardData {
  task_id: number
  title: string
  status: string
  current_stage_order: number
  progress: number
  stages: StageItem[]
}

export interface TaskItem {
  id: number
  template_id: number
  title: string
  status: string
  current_stage_order: number
  creator_id: number
  created_at: string
  updated_at: string
  template?: { id: number; name: string }
  stages?: StageItem[]
}

export const taskInstancesApi = {
  getList: (status?: string) => get<{ items: TaskItem[]; total: number }>('/task-instances', { status }),
  getDetail: (id: number) => get<TaskItem>(`/task-instances/${id}`),
  create: (data: { template_id: number; title?: string }) => post<TaskItem>('/task-instances', data),
  update: (id: number, data: any) => put<TaskItem>(`/task-instances/${id}`, data),
  delete: (id: number) => del(`/task-instances/${id}`),
  advance: (id: number) => put<TaskItem>(`/task-instances/${id}/advance`),
  getBoard: (id: number) => get<BoardData>(`/task-instances/${id}/board`),
  uploadToSlot: (taskId: number, stageId: number, slotId: number, data: { document_id: number; maturity?: string; maturity_note?: string | null }) =>
    post<SlotItem>(`/task-instances/${taskId}/stages/${stageId}/slots/${slotId}/upload`, data),
  replaceSlot: (taskId: number, stageId: number, slotId: number, data: { document_id: number; maturity?: string; maturity_note?: string | null }) =>
    put<SlotItem>(`/task-instances/${taskId}/stages/${stageId}/slots/${slotId}/replace`, data),
  removeSlotDoc: (taskId: number, stageId: number, slotId: number) =>
    del(`/task-instances/${taskId}/stages/${stageId}/slots/${slotId}/document`),
  updateMaturity: (taskId: number, stageId: number, slotId: number, data: { maturity: string; maturity_note?: string | null }) =>
    put(`/task-instances/${taskId}/stages/${stageId}/slots/${slotId}/maturity`, data),
  waiveSlot: (taskId: number, stageId: number, slotId: number, reason: string) =>
    put(`/task-instances/${taskId}/stages/${stageId}/slots/${slotId}/waive`, { reason }),
  unwaiveSlot: (taskId: number, stageId: number, slotId: number) =>
    put(`/task-instances/${taskId}/stages/${stageId}/slots/${slotId}/unwaive`),
  getSlotVersions: (taskId: number, stageId: number, slotId: number) =>
    get(`/task-instances/${taskId}/stages/${stageId}/slots/${slotId}/versions`),
}

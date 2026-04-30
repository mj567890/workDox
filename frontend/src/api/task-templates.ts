import { get, post, put, del } from './index'

export interface SlotTemplateItem {
  id: number
  name: string
  description: string | null
  is_required: boolean
  file_type_hints: string[] | null
  auto_tags: string[] | null
  sort_order: number
}

export interface StageTemplateItem {
  id: number
  template_id: number
  name: string
  order: number
  description: string | null
  deadline_offset_days: number | null
  slots: SlotTemplateItem[]
}

export interface TemplateItem {
  id: number
  name: string
  description: string | null
  category: string | null
  is_system: boolean
  stages: StageTemplateItem[]
}

export const taskTemplatesApi = {
  getList: (category?: string) => get<{ items: TemplateItem[]; total: number }>('/task-templates', { category }),
  getDetail: (id: number) => get<TemplateItem>(`/task-templates/${id}`),
  create: (data: any) => post<TemplateItem>('/task-templates', data),
  update: (id: number, data: any) => put(`/task-templates/${id}`, data),
  delete: (id: number) => del(`/task-templates/${id}`),
  clone: (id: number) => post<TemplateItem>(`/task-templates/${id}/clone`),
  addStage: (templateId: number, data: any) => post(`/task-templates/${templateId}/stages`, data),
  updateStage: (templateId: number, stageId: number, data: any) => put(`/task-templates/${templateId}/stages/${stageId}`, data),
  deleteStage: (templateId: number, stageId: number) => del(`/task-templates/${templateId}/stages/${stageId}`),
  reorderStages: (templateId: number, ids: number[]) => put(`/task-templates/${templateId}/stages/reorder`, { ids }),
  addSlot: (templateId: number, stageId: number, data: any) => post(`/task-templates/${templateId}/stages/${stageId}/slots`, data),
  updateSlot: (templateId: number, stageId: number, slotId: number, data: any) => put(`/task-templates/${templateId}/stages/${stageId}/slots/${slotId}`, data),
  deleteSlot: (templateId: number, stageId: number, slotId: number) => del(`/task-templates/${templateId}/stages/${stageId}/slots/${slotId}`),
}

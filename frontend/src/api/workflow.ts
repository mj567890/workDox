import { get, post, put, del } from './index'
import type { PaginatedResponse } from './documents'

export interface WorkflowTemplateItem {
  id: number
  name: string
  matter_type_id: number
  matter_type_name: string
  is_active: boolean
  description: string | null
  node_count: number
  created_at: string
}

export interface TemplateNodeItem {
  id: number
  template_id: number
  node_name: string
  node_order: number
  owner_role: string
  sla_hours: number | null
  required_documents_rule: Record<string, any> | null
  description: string | null
}

export interface NodeValidation {
  valid: boolean
  missing_documents: string[]
  warnings: string[]
}

export const workflowApi = {
  getTemplates: (params?: Record<string, any>) => get<PaginatedResponse<WorkflowTemplateItem>>('/workflow/templates', params),
  createTemplate: (data: Record<string, any>) => post<WorkflowTemplateItem>('/workflow/templates', data),
  getTemplateDetail: (id: number) => get<{ template: WorkflowTemplateItem; nodes: TemplateNodeItem[] }>(`/workflow/templates/${id}`),
  updateTemplate: (id: number, data: Record<string, any>) => put(`/workflow/templates/${id}`, data),
  deleteTemplate: (id: number) => del(`/workflow/templates/${id}`),
  getNodes: (matterId: number) => get(`/matters/${matterId}/nodes`),
  advanceNode: (matterId: number, nodeId: number, data?: { comment?: string }) => put(`/matters/${matterId}/nodes/${nodeId}/advance`, data || {}),
  rollbackNode: (matterId: number, nodeId: number) => put(`/matters/${matterId}/nodes/${nodeId}/rollback`),
  skipNode: (matterId: number, nodeId: number) => put(`/matters/${matterId}/nodes/${nodeId}/skip`),
  validateNode: (matterId: number, nodeId: number) => get<NodeValidation>(`/matters/${matterId}/nodes/${nodeId}/validate`),
}

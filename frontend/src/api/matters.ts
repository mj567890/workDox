import { get, post, put, del } from './index'
import type { PaginatedResponse, DocumentItem } from './documents'

export interface MatterItem {
  id: number
  matter_no: string
  title: string
  type_id: number
  type_name: string
  owner_id: number
  owner_name: string
  status: string
  is_key_project: boolean
  progress: number
  current_node_id: number | null
  current_node_name: string | null
  due_date: string | null
  description: string | null
  member_count: number
  document_count: number
  created_at: string
  updated_at: string
}

export interface MatterDetail extends MatterItem {
  members: MatterMember[]
  documents: DocumentItem[]
  nodes: WorkflowNode[]
  recent_comments: MatterComment[]
}

export interface MatterMember {
  id: number
  user_id: number
  user_name: string
  role_in_matter: string
  avatar_url: string | null
  joined_at: string
}

export interface MatterComment {
  id: number
  matter_id: number
  user_id: number
  user_name: string
  content: string
  created_at: string
}

export interface WorkflowNode {
  id: number
  matter_id: number
  node_name: string
  node_order: number
  owner_id: number
  owner_name: string
  status: string
  sla_status: string | null
  planned_finish_time: string | null
  actual_finish_time: string | null
  description: string | null
  required_documents_rule: Record<string, any> | null
  created_at: string
}

export const mattersApi = {
  getList: (params?: Record<string, any>) => get<PaginatedResponse<MatterItem>>('/matters', params),
  create: (data: Record<string, any>) => post<MatterItem>('/matters', data),
  getDetail: (id: number) => get<MatterDetail>(`/matters/${id}`),
  update: (id: number, data: Record<string, any>) => put<MatterItem>(`/matters/${id}`, data),
  delete: (id: number) => del(`/matters/${id}`),
  updateStatus: (id: number, data: { status: string; comment?: string }) => put(`/matters/${id}/status`, data),
  getMembers: (id: number) => get<MatterMember[]>(`/matters/${id}/members`),
  addMembers: (id: number, data: { user_ids: number[]; role_in_matter?: string }) => post(`/matters/${id}/members`, data),
  removeMember: (id: number, userId: number) => del(`/matters/${id}/members/${userId}`),
  getComments: (id: number, params?: Record<string, any>) => get<PaginatedResponse<MatterComment>>(`/matters/${id}/comments`, params),
  addComment: (id: number, data: { content: string }) => post<MatterComment>(`/matters/${id}/comments`, data),
  getDocuments: (id: number, params?: Record<string, any>) => get<PaginatedResponse<DocumentItem>>(`/matters/${id}/documents`, params),
}

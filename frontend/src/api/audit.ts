import { get } from './index'
import type { PaginatedResponse } from './documents'

export interface AuditLogItem {
  id: number
  user_id: number
  user_name: string
  operation_type: string
  target_type: string
  target_id: number | null
  detail: string | null
  ip_address: string | null
  created_at: string
}

export const auditApi = {
  getList: (params?: Record<string, any>) => get<PaginatedResponse<AuditLogItem>>('/audit-logs', params),
}

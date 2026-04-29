import { getPublic } from './index'

export interface PublicOverview {
  total_matters: number
  total_documents: number
  completed_matters: number
  in_progress_matters: number
  overdue_matters: number
  completion_rate: number
}

export interface PublicKeyProject {
  matter_id: number
  matter_no: string
  title: string
  progress: number
  status: string
  owner_name: string | null
  due_date: string | null
  risk_level: string
}

export interface PublicRiskAlert {
  matter_id: number
  matter_no: string
  title: string
  risk_type: string
  risk_level: string
  description: string
}

export interface PublicProgressChart {
  labels: string[]
  completed: number[]
  in_progress: number[]
  pending: number[]
}

export interface PublicTypeDistribution {
  name: string
  count: number
  percentage: number
}

export interface PublicMonthlyTrend {
  month: string
  total: number
  completed: number
  overdue: number
}

export interface PublicDepartmentWorkload {
  department_name: string
  total_matters: number
  completed_matters: number
  overdue_matters: number
  avg_progress: number
}

export interface PublicAdvancedAnalytics {
  departments: PublicDepartmentWorkload[]
  monthly_trend: PublicMonthlyTrend[]
  priority_breakdown: { priority: string; count: number }[]
}

export const publicDashboardApi = {
  getOverview: () => getPublic<PublicOverview>('/public/dashboard/overview'),
  getKeyProjects: () => getPublic<PublicKeyProject[]>('/public/dashboard/key-projects'),
  getRisks: () => getPublic<PublicRiskAlert[]>('/public/dashboard/risks'),
  getProgressChart: () => getPublic<PublicProgressChart>('/public/dashboard/progress-chart'),
  getTypeDistribution: () => getPublic<PublicTypeDistribution[]>('/public/dashboard/type-distribution'),
  getAdvancedAnalytics: () => getPublic<PublicAdvancedAnalytics>('/public/dashboard/advanced'),
}

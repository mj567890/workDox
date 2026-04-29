import { get } from './index'
import type { PaginatedResponse } from './documents'

export interface DashboardOverview {
  total_matters: number
  in_progress_matters: number
  overdue_matters: number
  completed_matters: number
  completion_rate: number
  total_documents: number
  pending_tasks: number
  risk_count: number
}

export interface KeyProjectItem {
  matter_id: number
  matter_no: string
  title: string
  owner_name: string
  progress: number
  status: string
  current_node: string | null
  due_date: string | null
  risk_level: string
}

export interface RiskAlertItem {
  matter_id: number
  matter_no: string
  title: string
  risk_type: string
  risk_level: string
  description: string
  days_overdue: number | null
}

export interface ProgressChartData {
  labels: string[]
  completed: number[]
  in_progress: number[]
  pending: number[]
}

export interface TypeDistributionData {
  name: string
  count: number
  percentage: number
}

export interface PersonalStats {
  week_completed_tasks: number
  week_total_tasks: number
  overdue_rate: number
  avg_completion_days: number
  streak_days: number
  priority_distribution: { priority: string; count: number }[]
}

export interface DepartmentWorkload {
  department_name: string
  total_matters: number
  completed_matters: number
  overdue_matters: number
  avg_progress: number
  workload_score: number
}

export interface MonthlyTrend {
  month: string
  total: number
  completed: number
  overdue: number
}

export interface AdvancedAnalytics {
  departments: DepartmentWorkload[]
  monthly_trend: MonthlyTrend[]
  priority_breakdown: { priority: string; count: number }[]
}

export const dashboardApi = {
  getOverview: () => get<DashboardOverview>('/dashboard/overview'),
  getKeyProjects: () => get<KeyProjectItem[]>('/dashboard/key-projects'),
  getRisks: () => get<RiskAlertItem[]>('/dashboard/risks'),
  getProgressChart: (period?: string) => get<ProgressChartData>('/dashboard/progress-chart', { period }),
  getTypeDistribution: () => get<TypeDistributionData[]>('/dashboard/type-distribution'),
  getPersonalStats: () => get<PersonalStats>('/dashboard/personal-stats'),
  getAdvancedAnalytics: () => get<AdvancedAnalytics>('/dashboard/advanced'),
}

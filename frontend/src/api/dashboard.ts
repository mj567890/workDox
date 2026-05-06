import { get } from './index'
import type { PaginatedResponse } from './documents'

export interface DashboardOverview {
  total_tasks: number
  active_tasks: number
  completed_tasks: number
  completion_rate: number
  pipeline_progress: number
  overdue_stages: number
  total_slots: number
  filled_slots: number
  total_documents: number
}

export interface KeyProjectItem {
  task_id: number
  title: string
  template_name: string
  current_stage: string
  current_stage_order: number
  progress: number
  status: string
  creator_id: number
  created_at: string | null
}

export interface RiskAlertItem {
  task_id: number
  title: string
  risk_type: string
  risk_level: string
  description: string
  stage_name: string
}

export interface ProgressChartData {
  funnel: { stage_order: number; count: number }[]
  trend: { month: string; total: number; completed: number }[]
}

export interface TypeDistributionData {
  name: string
  count: number
}

export interface PersonalStats {
  week_completed_tasks: number
  week_total_tasks: number
  overdue_rate: number
  avg_completion_days: number
  streak_days: number
  total_tasks: number
  status_distribution: { status: string; label: string; count: number }[]
}

export interface DepartmentWorkload {
  department_name: string
  total_tasks: number
  completed_tasks: number
}

export interface MonthlyTrend {
  month: string
  total: number
  completed: number
}

export interface AdvancedAnalytics {
  monthly_trend: MonthlyTrend[]
  department_workload: DepartmentWorkload[]
  template_distribution: TypeDistributionData[]
  status_distribution: { status: string; label: string; count: number }[]
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

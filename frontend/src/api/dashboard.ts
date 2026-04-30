import { get } from './index'

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

export interface ActiveTaskItem {
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
  stage_name: string | null
  days_stalled: number | null
  days_overdue: number | null
}

export interface StageFunnelItem {
  stage_order: number
  count: number
}

export interface TemplateDistItem {
  name: string
  count: number
}

export interface StatusDistItem {
  status: string
  label: string
  count: number
}

export interface MonthlyTrendItem {
  month: string
  total: number
  completed: number
}

export interface DeptWorkloadItem {
  department_name: string
  total_tasks: number
  completed_tasks: number
}

export interface AdvancedAnalytics {
  departments: DeptWorkloadItem[]
  monthly_trend: MonthlyTrendItem[]
  status_distribution: StatusDistItem[]
  stage_funnel: StageFunnelItem[]
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

export const dashboardApi = {
  getOverview: () => get<DashboardOverview>('/dashboard/overview'),
  getActiveTasks: () => get<ActiveTaskItem[]>('/dashboard/active-tasks'),
  getRisks: () => get<RiskAlertItem[]>('/dashboard/risks'),
  getStageFunnel: () => get<StageFunnelItem[]>('/dashboard/stage-funnel'),
  getTemplateDistribution: () => get<TemplateDistItem[]>('/dashboard/template-distribution'),
  getPersonalStats: () => get<PersonalStats>('/dashboard/personal-stats'),
  getAdvancedAnalytics: () => get<AdvancedAnalytics>('/dashboard/advanced'),
}

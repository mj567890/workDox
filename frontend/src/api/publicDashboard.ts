import { getPublic } from './index'

export interface PublicOverview {
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

export interface PublicAnalytics {
  monthly_trend: MonthlyTrendItem[]
  template_distribution: TemplateDistItem[]
  status_distribution: StatusDistItem[]
  stage_funnel: StageFunnelItem[]
  departments: DeptWorkloadItem[]
}

export const publicDashboardApi = {
  getOverview: () => getPublic<PublicOverview>('/public/dashboard/overview'),
  getActiveTasks: () => getPublic<ActiveTaskItem[]>('/public/dashboard/active-tasks'),
  getRisks: () => getPublic<RiskAlertItem[]>('/public/dashboard/risks'),
  getStageFunnel: () => getPublic<StageFunnelItem[]>('/public/dashboard/stage-funnel'),
  getTemplateDistribution: () => getPublic<TemplateDistItem[]>('/public/dashboard/template-distribution'),
  getAnalytics: () => getPublic<PublicAnalytics>('/public/dashboard/analytics'),
}

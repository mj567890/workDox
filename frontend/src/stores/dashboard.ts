import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardApi, type DashboardOverview, type KeyProjectItem, type RiskAlertItem, type ProgressChartData, type TypeDistributionData } from '@/api/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  const overview = ref<DashboardOverview | null>(null)
  const keyProjects = ref<KeyProjectItem[]>([])
  const riskAlerts = ref<RiskAlertItem[]>([])
  const progressChart = ref<ProgressChartData | null>(null)
  const typeDistribution = ref<TypeDistributionData[]>([])

  async function fetchOverview() {
    overview.value = await dashboardApi.getOverview()
  }

  async function fetchKeyProjects() {
    keyProjects.value = await dashboardApi.getKeyProjects()
  }

  async function fetchRiskAlerts() {
    riskAlerts.value = await dashboardApi.getRisks()
  }

  async function fetchProgressChart(period?: string) {
    progressChart.value = await dashboardApi.getProgressChart(period)
  }

  async function fetchTypeDistribution() {
    typeDistribution.value = await dashboardApi.getTypeDistribution()
  }

  async function fetchAll() {
    await Promise.all([
      fetchOverview(),
      fetchKeyProjects(),
      fetchRiskAlerts(),
      fetchProgressChart(),
      fetchTypeDistribution(),
    ])
  }

  return {
    overview,
    keyProjects,
    riskAlerts,
    progressChart,
    typeDistribution,
    fetchOverview,
    fetchKeyProjects,
    fetchRiskAlerts,
    fetchProgressChart,
    fetchTypeDistribution,
    fetchAll,
  }
})

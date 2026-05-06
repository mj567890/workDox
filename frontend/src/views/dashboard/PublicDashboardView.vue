<template>
  <div class="public-dashboard">
    <div class="dashboard-header">
      <h2>数据看板</h2>
      <p class="dashboard-subtitle">任务管线全流程概览</p>
    </div>

    <div v-if="loading">
      <el-row :gutter="16">
        <el-col :span="4" v-for="i in 6" :key="i">
          <el-skeleton animated>
            <template #template>
              <el-skeleton-item variant="card" style="height: 120px" />
            </template>
          </el-skeleton>
        </el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top: 20px">
        <el-col :span="14"><el-skeleton :rows="8" animated /></el-col>
        <el-col :span="10"><el-skeleton :rows="8" animated /></el-col>
      </el-row>
    </div>

    <div v-else>
      <!-- Stat Cards -->
      <el-row :gutter="16" class="stat-cards">
        <el-col :span="4">
          <el-card shadow="hover" class="stat-card stat-total">
            <div class="stat-value">{{ overview?.total_tasks || 0 }}</div>
            <div class="stat-label">总任务数</div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card shadow="hover" class="stat-card stat-active">
            <div class="stat-value">{{ overview?.active_tasks || 0 }}</div>
            <div class="stat-label">进行中</div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card shadow="hover" class="stat-card stat-completed">
            <div class="stat-value">{{ overview?.completed_tasks || 0 }}</div>
            <div class="stat-label">已完成</div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card shadow="hover" class="stat-card stat-rate">
            <div class="stat-value">{{ overview?.completion_rate || 0 }}%</div>
            <div class="stat-label">完成率</div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card shadow="hover" class="stat-card stat-pipeline">
            <div class="stat-value">{{ overview?.pipeline_progress || 0 }}%</div>
            <div class="stat-label">管线进度</div>
            <div class="stat-sub">{{ overview?.filled_slots || 0 }}/{{ overview?.total_slots || 0 }} 槽位</div>
          </el-card>
        </el-col>
        <el-col :span="4">
          <el-card shadow="hover" class="stat-card stat-overdue">
            <div class="stat-value">{{ overview?.overdue_stages || 0 }}</div>
            <div class="stat-label">逾期阶段</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- Active Tasks + Risk Alerts -->
      <el-row :gutter="16" class="mt-20">
        <el-col :span="14">
          <el-card header="活跃任务管线" shadow="never">
            <el-table :data="activeTasks" stripe size="small" max-height="420">
              <el-table-column prop="title" label="任务" min-width="180" show-overflow-tooltip />
              <el-table-column prop="template_name" label="模板" width="120" />
              <el-table-column prop="current_stage" label="当前阶段" width="100" />
              <el-table-column prop="progress" label="进度" width="140">
                <template #default="{ row }">
                  <el-progress :percentage="row.progress" :stroke-width="6" :status="row.progress >= 100 ? 'success' : undefined" />
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <el-col :span="10">
          <el-card header="风险预警" shadow="never">
            <div class="risk-list">
              <div v-for="item in riskAlerts.slice(0, 8)" :key="`${item.task_id}-${item.risk_type}`" class="risk-item">
                <div class="risk-header">
                  <el-tag :type="item.risk_level === 'high' ? 'danger' : 'warning'" size="small">
                    {{ item.risk_type }}
                  </el-tag>
                  <span class="risk-title">{{ item.title }}</span>
                </div>
                <div class="risk-desc">{{ item.description }}</div>
              </div>
              <el-empty v-if="riskAlerts.length === 0" description="暂无风险预警" :image-size="60" />
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- Stage Funnel + Template Distribution -->
      <el-row :gutter="16" class="mt-20">
        <el-col :span="12">
          <el-card header="阶段漏斗" shadow="never">
            <div ref="funnelChartRef" style="height: 320px"></div>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card header="模板分类分布" shadow="never">
            <div ref="templateChartRef" style="height: 320px"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- Monthly Trend + Status Distribution -->
      <el-row :gutter="16" class="mt-20">
        <el-col :span="14">
          <el-card header="月度趋势" shadow="never">
            <div ref="trendChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card header="任务状态分布" shadow="never">
            <div ref="statusChartRef" style="height: 300px"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- Department Workload -->
      <el-row :gutter="16" class="mt-20" v-if="analytics?.departments?.length">
        <el-col :span="24">
          <el-card header="部门工作量" shadow="never">
            <div ref="deptChartRef" style="height: 280px"></div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { publicDashboardApi, type PublicOverview, type ActiveTaskItem, type RiskAlertItem, type PublicAnalytics } from '@/api/publicDashboard'

const loading = ref(true)
const overview = ref<PublicOverview | null>(null)
const activeTasks = ref<ActiveTaskItem[]>([])
const riskAlerts = ref<RiskAlertItem[]>([])
const analytics = ref<PublicAnalytics | null>(null)

const funnelChartRef = ref<HTMLElement>()
const templateChartRef = ref<HTMLElement>()
const trendChartRef = ref<HTMLElement>()
const statusChartRef = ref<HTMLElement>()
const deptChartRef = ref<HTMLElement>()

const charts: echarts.ECharts[] = []

onMounted(async () => {
  try {
    const [ov, tasks, risks, an] = await Promise.all([
      publicDashboardApi.getOverview(),
      publicDashboardApi.getActiveTasks(),
      publicDashboardApi.getRisks(),
      publicDashboardApi.getAnalytics(),
    ])
    overview.value = ov
    activeTasks.value = tasks
    riskAlerts.value = risks
    analytics.value = an
  } finally {
    loading.value = false
  }

  await nextTick()
  if (analytics.value?.stage_funnel?.length) renderFunnelChart()
  if (analytics.value?.template_distribution?.length) renderTemplateChart()
  if (analytics.value?.monthly_trend?.length) renderTrendChart()
  if (analytics.value?.status_distribution?.length) renderStatusChart()
  if (analytics.value?.departments?.length) renderDeptChart()
})

onUnmounted(() => {
  charts.forEach(c => c.dispose())
})

function statusTag(s: string) {
  const map: Record<string, string> = { pending: 'info', active: 'warning', completed: 'success', cancelled: 'danger' }
  return map[s] || 'info'
}

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: '待开始', active: '进行中', completed: '已完成', cancelled: '已取消' }
  return map[s] || s
}

// ── Charts ────────────────────────────────────────────────────

function renderFunnelChart() {
  if (!funnelChartRef.value) return
  const chart = echarts.init(funnelChartRef.value)
  charts.push(chart)
  const data = analytics.value!.stage_funnel
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 个任务' },
    series: [{
      type: 'funnel', left: '10%', right: '10%', top: 20, bottom: 20,
      minSize: '20%', maxSize: '100%', gap: 2,
      label: { show: true, position: 'inside', fontSize: 13 },
      data: data.map(d => ({ name: `阶段${d.stage_order}`, value: d.count })),
    }],
  })
}

function renderTemplateChart() {
  if (!templateChartRef.value) return
  const chart = echarts.init(templateChartRef.value)
  charts.push(chart)
  const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399', '#00D4FF', '#9C27B0']
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], center: ['50%', '55%'],
      data: analytics.value!.template_distribution.map((d, i) => ({
        name: d.name, value: d.count,
        itemStyle: { color: colors[i % colors.length] },
      })),
      label: { formatter: '{b}\n{c}' },
    }],
  })
}

function renderTrendChart() {
  if (!trendChartRef.value) return
  const chart = echarts.init(trendChartRef.value)
  charts.push(chart)
  const data = analytics.value!.monthly_trend
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['创建', '完成'] },
    xAxis: { type: 'category', data: data.map(d => d.month), axisLabel: { rotate: 45 } },
    yAxis: { type: 'value', name: '任务数' },
    series: [
      { name: '创建', type: 'line', data: data.map(d => d.total), color: '#409EFF', smooth: true },
      { name: '完成', type: 'line', data: data.map(d => d.completed), color: '#67C23A', smooth: true },
    ],
    grid: { bottom: 60, left: 50, right: 20 },
  })
}

function renderStatusChart() {
  if (!statusChartRef.value) return
  const chart = echarts.init(statusChartRef.value)
  charts.push(chart)
  const colors: Record<string, string> = { pending: '#909399', active: '#409EFF', completed: '#67C23A', cancelled: '#F56C6C' }
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie', radius: '70%', center: ['50%', '50%'],
      data: analytics.value!.status_distribution.map(d => ({
        name: d.label, value: d.count,
        itemStyle: { color: colors[d.status] || '#909399' },
      })),
      label: { formatter: '{b}: {c}' },
    }],
  })
}

function renderDeptChart() {
  if (!deptChartRef.value) return
  const chart = echarts.init(deptChartRef.value)
  charts.push(chart)
  const data = [...analytics.value!.departments].reverse()
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', name: '任务数' },
    yAxis: { type: 'category', data: data.map(d => d.department_name), axisLabel: { fontSize: 11 } },
    series: [
      { name: '已完成', type: 'bar', stack: 'total', data: data.map(d => d.completed_tasks), color: '#67C23A', label: { show: true, position: 'inside' } },
      { name: '其他', type: 'bar', stack: 'total', data: data.map(d => d.total_tasks - d.completed_tasks), color: '#E6A23C', label: { show: true, position: 'inside' } },
    ],
    grid: { left: 100 },
  })
}
</script>

<style scoped>
.public-dashboard {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px 32px;
}
.dashboard-header { margin-bottom: 24px; }
.dashboard-header h2 { margin: 0; font-size: 24px; font-weight: 700; color: #303133; }
.dashboard-subtitle { margin: 4px 0 0; font-size: 14px; color: #909399; }
.mt-20 { margin-top: 20px; }
.stat-cards { margin-bottom: 0; }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: 700; }
.stat-total .stat-value { color: #409EFF; }
.stat-active .stat-value { color: #E6A23C; }
.stat-completed .stat-value { color: #67C23A; }
.stat-rate .stat-value { color: #409EFF; }
.stat-pipeline .stat-value { color: #00D4FF; }
.stat-overdue .stat-value { color: #F56C6C; }
.stat-label { font-size: 13px; color: #999; margin-top: 4px; }
.stat-sub { font-size: 11px; color: #c0c4cc; margin-top: 4px; }
.risk-list { max-height: 420px; overflow-y: auto; }
.risk-item { padding: 10px; border-bottom: 1px solid #f5f5f5; }
.risk-item:hover { background: #f5f5f5; }
.risk-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.risk-title { font-weight: 600; font-size: 13px; }
.risk-desc { font-size: 12px; color: #666; }
</style>

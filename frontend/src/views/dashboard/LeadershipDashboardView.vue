<template>
  <div class="dashboard-view">
    <h2>领导驾驶舱</h2>

    <div v-if="loading">
      <el-row :gutter="16">
        <el-col :span="6" v-for="i in 4" :key="i">
          <el-skeleton animated>
            <template #template>
              <el-skeleton-item variant="card" style="height: 120px" />
            </template>
          </el-skeleton>
        </el-col>
      </el-row>
      <el-row :gutter="16" style="margin-top: 20px">
        <el-col :span="12">
          <el-skeleton animated>
            <template #template>
              <el-skeleton-item variant="rect" style="height: 300px" />
            </template>
          </el-skeleton>
        </el-col>
        <el-col :span="12">
          <el-skeleton animated>
            <template #template>
              <el-skeleton-item variant="rect" style="height: 300px" />
            </template>
          </el-skeleton>
        </el-col>
      </el-row>
      <el-skeleton :rows="5" animated style="margin-top: 20px" />
    </div>
    <div v-else>
      <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-total" @click="showDrillDown('total')">
          <div class="stat-value">{{ overview?.total_matters || 0 }}</div>
          <div class="stat-label">总事项数</div>
          <div class="stat-hint">点击查看明细</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-progress" @click="showDrillDown('in_progress')">
          <div class="stat-value">{{ overview?.in_progress_matters || 0 }}</div>
          <div class="stat-label">进行中</div>
          <div class="stat-hint">点击查看明细</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-overdue" @click="showDrillDown('overdue')">
          <div class="stat-value">{{ overview?.overdue_matters || 0 }}</div>
          <div class="stat-label">已逾期</div>
          <div class="stat-hint">点击查看明细</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card stat-complete">
          <div class="stat-value">{{ ((overview?.completion_rate || 0) * 100).toFixed(1) }}%</div>
          <div class="stat-label">完成率</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="12">
        <el-card header="重点工作看板" shadow="never">
          <el-table :data="keyProjects" stripe size="small">
            <el-table-column prop="title" label="事项" min-width="180" />
            <el-table-column prop="owner_name" label="负责人" width="100" />
            <el-table-column prop="progress" label="进度" width="120">
              <template #default="{ row }">
                <el-progress :percentage="row.progress" :stroke-width="6" :status="row.risk_level === 'high' ? 'exception' : undefined" />
              </template>
            </el-table-column>
            <el-table-column prop="risk_level" label="风险" width="70">
              <template #default="{ row }">
                <el-tag v-if="row.risk_level === 'high'" type="danger" size="small">高</el-tag>
                <el-tag v-else-if="row.risk_level === 'medium'" type="warning" size="small">中</el-tag>
                <el-tag v-else type="success" size="small">低</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click="$router.push('/task-mgmt')">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card header="风险预警" shadow="never">
          <div class="risk-list">
            <div v-for="item in riskAlerts" :key="item.task_id" class="risk-item" @click="$router.push('/task-mgmt')">
              <div class="risk-header">
                <el-tag :type="item.risk_level === 'high' ? 'danger' : 'warning'" size="small">
                  {{ item.risk_type }}
                </el-tag>
                <span class="risk-title">{{ item.title }}</span>
              </div>
              <div class="risk-desc">{{ item.description }}</div>
              <div v-if="item.days_overdue" class="risk-days">逾期 {{ item.days_overdue }} 天</div>
            </div>
            <el-empty v-if="riskAlerts.length === 0" description="暂无风险预警" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="12">
        <el-card header="月度进度统计" shadow="never">
          <div ref="progressChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="事项类型分布" shadow="never">
          <div ref="typeChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Advanced Analytics -->
    <el-row :gutter="20" class="mt-20">
      <el-col :span="14">
        <el-card header="月度趋势对比" shadow="never">
          <div ref="trendChartRef" style="height: 320px"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card header="部门工作量分布" shadow="never">
          <div ref="deptChartRef" style="height: 320px"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card header="任务优先级分布" shadow="never">
          <div ref="priorityChartRef" style="height: 250px"></div>
        </el-card>
      </el-col>
    </el-row>
    </div>

    <!-- Drill-down Dialog -->
    <el-dialog v-model="drillDownVisible" :title="drillDownTitle" width="80%" :fullscreen="false">
      <el-table :data="drillDownData" stripe max-height="400">
        <el-table-column prop="title" label="事项名称" min-width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <StatusTag :status="row.status" type="matter" />
          </template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="120">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="6" :status="row.status === 'overdue' ? 'exception' : undefined" />
          </template>
        </el-table-column>
        <el-table-column prop="owner_name" label="负责人" width="100" />
        <el-table-column prop="due_date" label="截止日期" width="120" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { dashboardApi } from '@/api/dashboard'
import StatusTag from '@/components/common/StatusTag.vue'
import * as echarts from 'echarts'

const dashboardStore = useDashboardStore()
const overview = ref(dashboardStore.overview)
const keyProjects = ref<any[]>([])
const riskAlerts = ref<any[]>([])
const loading = ref(true)

const progressChartRef = ref<HTMLElement>()
const typeChartRef = ref<HTMLElement>()
const trendChartRef = ref<HTMLElement>()
const deptChartRef = ref<HTMLElement>()
const priorityChartRef = ref<HTMLElement>()

// Drill-down
const drillDownVisible = ref(false)
const drillDownTitle = ref('')
const drillDownData = ref<any[]>([])

onMounted(async () => {
  loading.value = true
  await dashboardStore.fetchAll()
  overview.value = dashboardStore.overview
  keyProjects.value = dashboardStore.keyProjects
  riskAlerts.value = dashboardStore.riskAlerts
  loading.value = false

  await nextTick()
  if (dashboardStore.progressChart) {
    renderProgressChart(dashboardStore.progressChart)
  }
  if (dashboardStore.typeDistribution?.length) {
    renderTypeChart(dashboardStore.typeDistribution)
  }

  // Load advanced analytics
  try {
    const advanced = await dashboardApi.getAdvancedAnalytics()
    if (advanced) {
      renderTrendChart(advanced.monthly_trend)
      renderDeptChart(advanced.departments)
      renderPriorityChart(advanced.priority_breakdown)
    }
  } catch {
    // advanced analytics not available
  }
})

function renderProgressChart(data: any) {
  if (!progressChartRef.value) return
  const chart = echarts.init(progressChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['已完成', '进行中', '待开始'] },
    xAxis: { type: 'category', data: data.labels },
    yAxis: { type: 'value' },
    series: [
      { name: '已完成', type: 'bar', stack: 'total', data: data.completed, color: '#67C23A' },
      { name: '进行中', type: 'bar', stack: 'total', data: data.in_progress, color: '#409EFF' },
      { name: '待开始', type: 'bar', stack: 'total', data: data.pending, color: '#E6A23C' },
    ],
  })
}

function renderTypeChart(data: any[]) {
  if (!typeChartRef.value) return
  const chart = echarts.init(typeChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: data.map((d: any) => ({ name: d.name, value: d.count })),
      label: { formatter: '{b}: {c}' },
    }],
  })
}

function renderTrendChart(data: any[]) {
  if (!trendChartRef.value || !data?.length) return
  const chart = echarts.init(trendChartRef.value)
  const months = data.map((d: any) => d.month)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['总数', '已完成', '逾期'] },
    xAxis: { type: 'category', data: months, axisLabel: { rotate: 45 } },
    yAxis: { type: 'value' },
    series: [
      { name: '总数', type: 'line', data: data.map((d: any) => d.total), color: '#409EFF', smooth: true },
      { name: '已完成', type: 'line', data: data.map((d: any) => d.completed), color: '#67C23A', smooth: true },
      { name: '逾期', type: 'line', data: data.map((d: any) => d.overdue), color: '#F56C6C', smooth: true },
    ],
    grid: { bottom: 60 },
  })
}

function renderDeptChart(data: any[]) {
  if (!deptChartRef.value || !data?.length) return
  const chart = echarts.init(deptChartRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'value',
      name: '事项数',
      axisLabel: { formatter: '{value}' },
    },
    yAxis: {
      type: 'category',
      data: data.map((d: any) => d.department_name).reverse(),
      axisLabel: { fontSize: 11 },
    },
    series: [
      {
        name: '已完成',
        type: 'bar',
        stack: 'total',
        data: data.map((d: any) => d.completed_matters).reverse(),
        color: '#67C23A',
        label: { show: true, position: 'inside' },
      },
      {
        name: '进行中/逾期',
        type: 'bar',
        stack: 'total',
        data: data.map((d: any) => d.total_matters - d.completed_matters).reverse(),
        color: '#E6A23C',
        label: { show: true, position: 'inside' },
      },
    ],
    grid: { left: 100 },
  })
}

function renderPriorityChart(data: any[]) {
  if (!priorityChartRef.value || !data?.length) return
  const chart = echarts.init(priorityChartRef.value)
  const priorityLabels: Record<string, string> = { low: '低', normal: '普通', high: '高', urgent: '紧急' }
  const priorityColors: Record<string, string> = { low: '#909399', normal: '#409EFF', high: '#E6A23C', urgent: '#F56C6C' }
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: data.map((d: any) => priorityLabels[d.priority] || d.priority) },
    yAxis: { type: 'value', name: '任务数' },
    series: [{
      type: 'bar',
      data: data.map((d: any) => ({
        value: d.count,
        itemStyle: { color: priorityColors[d.priority] || '#409EFF' },
      })),
      barWidth: '50%',
      label: { show: true, position: 'top' },
    }],
  })
}

// Drill-down on stat cards
function showDrillDown(type: string) {
  drillDownTitle.value = type === 'overdue' ? '逾期事项明细' :
    type === 'in_progress' ? '进行中事项明细' : '事项明细'

  // Use key projects + risk alerts data for drill-down
  const allItems = [
    ...keyProjects.value.map((kp: any) => ({ ...kp, owner_name: kp.owner_name })),
  ]
  if (type === 'overdue') {
    drillDownData.value = allItems.filter((item: any) => item.status === 'overdue' || item.risk_level === 'high')
  } else if (type === 'in_progress') {
    drillDownData.value = allItems.filter((item: any) => item.status === 'in_progress')
  } else {
    drillDownData.value = allItems
  }
  drillDownVisible.value = true
}
</script>

<style scoped>
.dashboard-view h2 { margin: 0 0 20px; }
.mt-20 { margin-top: 20px; }
.stat-cards { margin-bottom: 0; }
.stat-card { text-align: center; }
.stat-value { font-size: 32px; font-weight: 700; }
.stat-total .stat-value { color: #409EFF; }
.stat-progress .stat-value { color: #E6A23C; }
.stat-overdue .stat-value { color: #F56C6C; }
.stat-complete .stat-value { color: #67C23A; }
.stat-label { font-size: 14px; color: #999; margin-top: 4px; }
.stat-hint { font-size: 11px; color: #c0c4cc; margin-top: 8px; opacity: 0; transition: opacity 0.3s; }
.stat-card:hover .stat-hint { opacity: 1; }
.stat-card { cursor: pointer; }
.risk-list { max-height: 300px; overflow-y: auto; }
.risk-item { padding: 10px; border-bottom: 1px solid #f5f5f5; cursor: pointer; }
.risk-item:hover { background: #f5f5f5; }
.risk-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.risk-title { font-weight: 600; font-size: 14px; }
.risk-desc { font-size: 13px; color: #666; }
.risk-days { font-size: 12px; color: #F56C6C; margin-top: 2px; }
</style>

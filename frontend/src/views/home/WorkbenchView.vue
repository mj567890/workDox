<template>
  <div class="workbench">
    <h2>个人工作台</h2>
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
      <el-skeleton :rows="5" animated style="margin-top: 20px" />
    </div>
    <div v-else>
      <el-row :gutter="20">
      <el-col :span="16">
        <el-card header="我的待办" class="mb-20">
          <el-table :data="taskStore.tasks" v-loading="taskStore.loading" stripe>
            <el-table-column prop="title" label="任务" min-width="200" />
            <el-table-column prop="matter_title" label="所属事项" width="150" />
            <el-table-column prop="priority" label="优先级" width="80">
              <template #default="{ row }">
                <StatusTag :status="row.priority" type="task_priority" />
              </template>
            </el-table-column>
            <el-table-column prop="due_time" label="截止时间" width="160">
              <template #default="{ row }">{{ formatDate(row.due_time) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button text type="primary" @click="$router.push(`/matters/${row.matter_id}`)">处理</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card header="我的统计" class="mb-20">
            <el-row :gutter="16">
              <el-col :span="6">
                <div class="stat-card stat-card-primary">
                  <div class="stat-card-label">本周完成任务</div>
                  <div class="stat-card-value">
                    <span class="stat-number">{{ personalStats.week_completed_tasks }}</span>
                    <span class="stat-total">/ {{ personalStats.week_total_tasks }}</span>
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card stat-card-warning">
                  <div class="stat-card-label">逾期率</div>
                  <div class="stat-card-value">
                    <span class="stat-number">{{ Math.round(personalStats.overdue_rate * 100) }}%</span>
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card stat-card-success">
                  <div class="stat-card-label">连续达标天数</div>
                  <div class="stat-card-value">
                    <span class="stat-number">{{ personalStats.streak_days }}</span>
                    <span class="stat-unit">天</span>
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card stat-card-danger">
                  <div class="stat-card-label">紧急任务数</div>
                  <div class="stat-card-value">
                    <span class="stat-number">{{ urgentTaskCount }}</span>
                  </div>
                </div>
              </el-col>
            </el-row>
            <div class="priority-distribution" style="margin-top: 16px">
              <span class="priority-title">优先级分布：</span>
              <el-tag
                v-for="item in priorityList"
                :key="item.priority"
                :type="priorityTagType(item.priority)"
                size="small"
                style="margin-right: 8px"
              >
                {{ priorityLabel(item.priority) }}: {{ item.count }}
              </el-tag>
              <span v-if="priorityList.length === 0" style="color: #999; font-size: 13px">暂无数据</span>
            </div>
          </el-card>

        <el-card header="我的事项">
          <el-table :data="matterStore.matters" v-loading="matterStore.loading" stripe>
            <el-table-column prop="matter_no" label="编号" width="140" />
            <el-table-column prop="title" label="事项名称" min-width="200" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <StatusTag :status="row.status" type="matter" />
              </template>
            </el-table-column>
            <el-table-column prop="progress" label="进度" width="120">
              <template #default="{ row }">
                <el-progress :percentage="row.progress" :stroke-width="8" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button text type="primary" @click="$router.push(`/matters/${row.id}`)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card header="最近通知" class="mb-20">
          <div v-for="item in notificationStore.notifications.slice(0, 8)" :key="item.id" class="notif-item" @click="$router.push(`/matters/${item.related_matter_id}`)">
            <el-badge :is-dot="!item.is_read" class="notif-dot" />
            <div>
              <div class="notif-title">{{ item.title }}</div>
              <div class="notif-time">{{ formatDate(item.created_at) }}</div>
            </div>
          </div>
          <el-empty v-if="notificationStore.notifications.length === 0" description="暂无通知" />
        </el-card>

        <el-card header="快速操作">
          <el-button type="primary" style="width: 100%; margin-bottom: 10px" @click="$router.push('/matters')">
            <el-icon><Plus /></el-icon>创建事项
          </el-button>
          <el-button style="width: 100%; margin-bottom: 10px" @click="$router.push('/documents')">
            <el-icon><Upload /></el-icon>上传文档
          </el-button>
          <el-button style="width: 100%" @click="$router.push('/tasks')">
            <el-icon><List /></el-icon>我的待办
          </el-button>
        </el-card>
      </el-col>
    </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Plus, Upload, List } from '@element-plus/icons-vue'
import { useTaskStore } from '@/stores/tasks'
import { useMatterStore } from '@/stores/matters'
import { useNotificationStore } from '@/stores/notifications'
import { dashboardApi, type PersonalStats } from '@/api/dashboard'
import { formatDate } from '@/utils/format'
import StatusTag from '@/components/common/StatusTag.vue'

const taskStore = useTaskStore()
const matterStore = useMatterStore()
const notificationStore = useNotificationStore()
const loading = ref(true)
const personalStats = ref<PersonalStats>({
  week_completed_tasks: 0,
  week_total_tasks: 0,
  overdue_rate: 0,
  avg_completion_days: 0,
  streak_days: 0,
  priority_distribution: [],
})

const priorityLabelMap: Record<string, string> = {
  low: '低',
  normal: '中',
  high: '高',
  urgent: '紧急',
}

const priorityTagTypeMap: Record<string, string> = {
  low: 'info',
  normal: '',
  high: 'warning',
  urgent: 'danger',
}

function priorityLabel(priority: string): string {
  return priorityLabelMap[priority] || priority
}

function priorityTagType(priority: string): string {
  return priorityTagTypeMap[priority] || ''
}

const priorityList = computed(() => {
  return personalStats.value.priority_distribution || []
})

const urgentTaskCount = computed(() => {
  return personalStats.value.priority_distribution
    .filter(item => item.priority === 'high' || item.priority === 'urgent')
    .reduce((sum, item) => sum + item.count, 0)
})

onMounted(async () => {
  loading.value = true
  await Promise.all([
    taskStore.fetchTasks({ page_size: 5 }),
    matterStore.fetchMatters({ page_size: 5 }),
    notificationStore.fetchNotifications({ page_size: 8 }),
    dashboardApi.getPersonalStats().then(data => {
      personalStats.value = data
    }).catch(() => {}),
  ])
  loading.value = false
})
</script>

<style scoped>
.workbench h2 {
  margin: 0 0 20px;
}
.mb-20 {
  margin-bottom: 20px;
}
.notif-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 0;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
}
.notif-item:last-child {
  border-bottom: none;
}
.notif-dot {
  margin-top: 6px;
}
.notif-title {
  font-size: 13px;
  line-height: 1.4;
}
.notif-time {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.stat-card {
  padding: 16px;
  border-radius: 6px;
  background: #fff;
  border-left: 4px solid #409eff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.2s;
}
.stat-card:hover {
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
}
.stat-card-primary {
  border-left-color: #409eff;
}
.stat-card-success {
  border-left-color: #67c23a;
}
.stat-card-warning {
  border-left-color: #e6a23c;
}
.stat-card-danger {
  border-left-color: #f56c6c;
}
.stat-card-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}
.stat-card-value {
  display: flex;
  align-items: baseline;
  gap: 2px;
}
.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}
.stat-total {
  font-size: 14px;
  color: #909399;
}
.stat-unit {
  font-size: 14px;
  color: #909399;
  margin-left: 2px;
}
.priority-title {
  font-size: 13px;
  color: #606266;
  margin-right: 8px;
}
</style>

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
            <el-table-column prop="template_name" label="模板" width="120">
              <template #default="{ row }">
                {{ row.template_name || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <StatusTag :status="row.status" type="task" />
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="160">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button text type="primary" @click="$router.push(`/task-mgmt`)">处理</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="taskStore.tasks.length === 0 && !taskStore.loading" description="暂无待办任务" />
        </el-card>

        <el-card header="我的统计" class="mb-20">
          <el-row :gutter="16">
            <el-col :span="6">
              <div class="stat-card stat-card-primary">
                <div class="stat-card-label">总任务数</div>
                <div class="stat-card-value">
                  <span class="stat-number">{{ personalStats.total_tasks }}</span>
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card stat-card-success">
                <div class="stat-card-label">本周完成</div>
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
              <div class="stat-card stat-card-danger">
                <div class="stat-card-label">连续达标天数</div>
                <div class="stat-card-value">
                  <span class="stat-number">{{ personalStats.streak_days }}</span>
                  <span class="stat-unit">天</span>
                </div>
              </div>
            </el-col>
          </el-row>
          <div class="status-distribution" style="margin-top: 16px" v-if="statusList.length > 0">
            <span class="dist-title">任务状态分布：</span>
            <el-tag
              v-for="item in statusList"
              :key="item.status"
              :type="statusTagType(item.status)"
              size="small"
              style="margin-right: 8px"
            >
              {{ item.label }}: {{ item.count }}
            </el-tag>
          </div>
        </el-card>

        <el-card header="最近任务">
          <el-table :data="taskStore.tasks.slice(0, 5)" v-loading="taskStore.loading" stripe>
            <el-table-column prop="title" label="任务名称" min-width="200" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <StatusTag :status="row.status" type="task" />
              </template>
            </el-table-column>
            <el-table-column prop="current_stage_order" label="当前阶段" width="100" />
            <el-table-column label="操作" width="100">
              <template #default>
                <el-button text type="primary" @click="$router.push('/task-mgmt')">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card header="最近通知" class="mb-20">
          <div v-for="item in notificationStore.notifications.slice(0, 8)" :key="item.id" class="notif-item">
            <el-badge :is-dot="!item.is_read" class="notif-dot" />
            <div>
              <div class="notif-title">{{ item.title }}</div>
              <div class="notif-time">{{ formatDate(item.created_at) }}</div>
            </div>
          </div>
          <el-empty v-if="notificationStore.notifications.length === 0" description="暂无通知" />
        </el-card>

        <el-card header="快速操作">
          <el-button type="primary" style="width: 100%; margin-bottom: 10px" @click="$router.push('/task-mgmt')">
            <el-icon><Plus /></el-icon>创建任务
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
import { useNotificationStore } from '@/stores/notifications'
import { dashboardApi, type PersonalStats } from '@/api/dashboard'
import { formatDate } from '@/utils/format'
import StatusTag from '@/components/common/StatusTag.vue'

const taskStore = useTaskStore()
const notificationStore = useNotificationStore()
const loading = ref(true)
const personalStats = ref<PersonalStats>({
  week_completed_tasks: 0,
  week_total_tasks: 0,
  overdue_rate: 0,
  avg_completion_days: 0,
  streak_days: 0,
  total_tasks: 0,
  status_distribution: [],
})

const statusTagTypeMap: Record<string, string> = {
  pending: 'info',
  active: '',
  completed: 'success',
  cancelled: 'danger',
}

function statusTagType(status: string): string {
  return statusTagTypeMap[status] || ''
}

const statusList = computed(() => {
  return personalStats.value.status_distribution || []
})

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([
      taskStore.fetchTasks({ page_size: 5 }),
      notificationStore.fetchNotifications({ page_size: 8 }),
      dashboardApi.getPersonalStats().then(data => {
        personalStats.value = data
      }).catch(() => {}),
    ])
  } catch {
    // Ignore individual failures, page should still render
  }
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
.dist-title {
  font-size: 13px;
  color: #606266;
  margin-right: 8px;
}
</style>

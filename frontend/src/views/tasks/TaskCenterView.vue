<template>
  <div class="task-center">
    <h2>待办中心</h2>
    <el-card shadow="never">
      <div class="toolbar">
        <el-select v-model="filterStatus" placeholder="状态" clearable @change="fetchData">
          <el-option label="待处理" value="pending" />
          <el-option label="处理中" value="in_progress" />
          <el-option label="已完成" value="completed" />
        </el-select>
        <el-select v-model="filterPriority" placeholder="优先级" clearable @change="fetchData">
          <el-option label="紧急" value="urgent" />
          <el-option label="高" value="high" />
          <el-option label="普通" value="normal" />
          <el-option label="低" value="low" />
        </el-select>
        <div style="flex: 1" />
        <el-dropdown @command="handleExport">
          <el-button type="default">
            导出 <el-icon><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
              <el-dropdown-item command="pdf" disabled>导出 PDF</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div v-if="hasSelection" class="batch-bar">
        <span class="batch-info">已选择 {{ selectedCount }} 项</span>
        <el-button type="primary" size="small" :loading="batchLoading" @click="handleBatchComplete">批量完成</el-button>
        <el-button size="small" @click="cancelSelection">取消选择</el-button>
      </div>

      <el-table ref="tableRef" :data="taskStore.tasks" v-loading="taskStore.loading" stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="title" label="任务" min-width="250" />
        <el-table-column prop="matter_title" label="所属事项" width="180" />
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }"><StatusTag :status="row.priority" type="task_priority" /></template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }"><StatusTag :status="row.status" type="task" /></template>
        </el-table-column>
        <el-table-column prop="assigner_name" label="分配人" width="100" />
        <el-table-column prop="due_time" label="截止时间" width="160">
          <template #default="{ row }">{{ formatDate(row.due_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending'" text type="primary" size="small" @click="handleStart(row.id)">开始</el-button>
            <el-button v-if="row.status === 'in_progress'" text type="success" size="small" @click="handleComplete(row.id)">完成</el-button>
            <el-button text size="small" @click="$router.push(`/matters/${row.matter_id}`)">查看事项</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="taskStore.total"
          layout="total, sizes, prev, pager, next"
          @change="fetchData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'
import { useTaskStore } from '@/stores/tasks'
import { usePagination } from '@/composables/usePagination'
import { useBatchSelection } from '@/composables/useBatchSelection'
import { post } from '@/api/index'
import { formatDate } from '@/utils/format'
import StatusTag from '@/components/common/StatusTag.vue'
import { ElMessage } from 'element-plus'

const taskStore = useTaskStore()
const { page, pageSize, setTotal } = usePagination()
const { selectedIds, selectedCount, hasSelection, clearSelection } = useBatchSelection<{ id: number }>()
const tableRef = ref()
const filterStatus = ref('')
const filterPriority = ref('')
const batchLoading = ref(false)

async function fetchData() {
  await taskStore.fetchTasks({
    page: page.value,
    page_size: pageSize.value,
    status: filterStatus.value || undefined,
    priority: filterPriority.value || undefined,
  })
  setTotal(taskStore.total)
}

function handleSelectionChange(rows: any[]) {
  selectedIds.value = new Set(rows.map(r => r.id))
}

function cancelSelection() {
  clearSelection()
  tableRef.value?.clearSelection()
}

async function handleBatchComplete() {
  if (selectedIds.value.size === 0) return
  batchLoading.value = true
  try {
    const res = await post('/tasks/batch/complete', { ids: Array.from(selectedIds.value) })
    ElMessage.success((res as any).detail || '批量完成成功')
    clearSelection()
    tableRef.value?.clearSelection()
    fetchData()
  } catch (e) {
    // Error handled by API interceptor
  } finally {
    batchLoading.value = false
  }
}

async function handleStart(id: number) {
  await taskStore.updateTask(id, { status: 'in_progress' })
  ElMessage.success('任务已开始')
  fetchData()
}

async function handleComplete(id: number) {
  await taskStore.updateTask(id, { status: 'completed' })
  ElMessage.success('任务已完成')
  fetchData()
}

async function handleExport(command: string) {
  if (command === 'excel') {
    const token = localStorage.getItem('token')
    const response = await fetch('/api/v1/tasks/export/excel', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `tasks_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
  }
}

onMounted(fetchData)
</script>

<style scoped>
.task-center h2 { margin: 0 0 20px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  margin-bottom: 12px;
  background: #ecf5ff;
  border-radius: 4px;
  border: 1px solid #b3d8ff;
}
.batch-info { font-size: 14px; color: #409eff; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>

<template>
  <div class="matter-list">
    <div class="page-header">
      <h2>业务事项</h2>
      <el-button type="primary" @click="showCreate = true" v-if="canCreateMatter">
        <el-icon><Plus /></el-icon>创建事项
      </el-button>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="keyword" placeholder="搜索事项" clearable style="width: 250px" @input="handleSearch" />
        <el-select v-model="filterStatus" placeholder="状态" clearable @change="fetchData">
          <el-option label="待开始" value="pending" />
          <el-option label="进行中" value="in_progress" />
          <el-option label="已暂停" value="paused" />
          <el-option label="已完成" value="completed" />
        </el-select>
        <el-select v-model="filterType" placeholder="事项类型" clearable @change="fetchData">
          <el-option v-for="t in matterTypes" :key="t.id" :label="t.name" :value="t.id" />
        </el-select>
        <el-checkbox v-model="filterKeyProject" @change="fetchData">仅重点工作</el-checkbox>
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
        <el-button type="primary" size="small" @click="showAssignDialog = true">批量分配</el-button>
        <el-button size="small" @click="cancelSelection">取消选择</el-button>
      </div>

      <div v-if="loading">
        <el-skeleton :rows="8" animated />
      </div>
      <div v-else>
        <el-table ref="tableRef" :data="matterStore.matters" stripe @selection-change="handleSelectionChange" @row-click="(row: any) => $router.push(`/matters/${row.id}`)" style="cursor: pointer">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="matter_no" label="编号" width="150" />
        <el-table-column prop="title" label="事项名称" min-width="250">
          <template #default="{ row }">
            <div class="matter-title">
              <el-tag v-if="row.is_key_project" type="danger" size="small" effect="dark">重点</el-tag>
              <span>{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }"><StatusTag :status="row.status" type="matter" /></template>
        </el-table-column>
        <el-table-column prop="progress" label="进度" width="150">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="8" :status="row.progress === 100 ? 'success' : undefined" />
          </template>
        </el-table-column>
        <el-table-column prop="owner_name" label="负责人" width="100" />
        <el-table-column prop="type_name" label="类型" width="120" />
        <el-table-column prop="due_date" label="截止日期" width="120">
          <template #default="{ row }">{{ formatDate(row.due_date, 'YYYY-MM-DD') }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click.stop="$router.push(`/matters/${row.id}`)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="matterStore.total"
          layout="total, sizes, prev, pager, next"
          @change="fetchData"
        />
      </div>
      </div>
    </el-card>

    <el-dialog v-model="showCreate" title="创建业务事项" width="600px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="事项名称" prop="title">
          <el-input v-model="form.title" placeholder="请输入事项名称" />
        </el-form-item>
        <el-form-item label="事项类型" prop="type_id">
          <el-select v-model="form.type_id" placeholder="选择事项类型">
            <el-option v-for="t in matterTypes" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人" prop="owner_id">
          <el-select v-model="form.owner_id" placeholder="选择负责人" filterable>
            <el-option v-for="u in userList" :key="u.id" :label="u.real_name" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="协作人">
          <el-select v-model="form.member_ids" placeholder="选择协作人" multiple filterable>
            <el-option v-for="u in userList" :key="u.id" :label="u.real_name" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="截止日期">
          <el-date-picker v-model="form.due_date" type="date" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="流程模板">
          <el-select v-model="form.workflow_template_id" placeholder="选择流程模板（可选）" clearable>
            <el-option v-for="t in templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="重点工作">
          <el-switch v-model="form.is_key_project" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showAssignDialog" title="批量分配" width="400px" @close="assigneeId = null">
      <el-form label-width="80px">
        <el-form-item label="新负责人">
          <el-select v-model="assigneeId" placeholder="选择负责人" filterable style="width: 100%">
            <el-option v-for="u in userList" :key="u.id" :label="u.real_name" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAssignDialog = false">取消</el-button>
        <el-button type="primary" :loading="assigning" :disabled="!assigneeId" @click="handleBatchAssign">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Plus, ArrowDown } from '@element-plus/icons-vue'
import { useMatterStore } from '@/stores/matters'
import { usePermission } from '@/composables/usePermission'
import { usePagination } from '@/composables/usePagination'
import { useBatchSelection } from '@/composables/useBatchSelection'
import { post } from '@/api/index'
import { usersApi } from '@/api/users'
import { workflowApi } from '@/api/workflow'
import { formatDate } from '@/utils/format'
import StatusTag from '@/components/common/StatusTag.vue'
import { ElMessage } from 'element-plus'

interface MatterType { id: number; name: string; code: string }

const matterStore = useMatterStore()
const { canCreateMatter } = usePermission()
const { page, pageSize, setTotal } = usePagination()
const { selectedIds, selectedCount, hasSelection, clearSelection } = useBatchSelection<{ id: number }>()
const tableRef = ref()
const loading = ref(true)

const keyword = ref('')
const filterStatus = ref('')
const filterType = ref<number | null>(null)
const filterKeyProject = ref(false)
const showCreate = ref(false)
const creating = ref(false)
const showAssignDialog = ref(false)
const assigneeId = ref<number | null>(null)
const assigning = ref(false)
const matterTypes = ref<MatterType[]>([])
const userList = ref<any[]>([])
const templates = ref<any[]>([])
const formRef = ref()

const form = reactive({
  title: '',
  type_id: null as number | null,
  owner_id: null as number | null,
  member_ids: [] as number[],
  due_date: null as Date | null,
  workflow_template_id: null as number | null,
  is_key_project: false,
  description: '',
})

const rules = {
  title: [{ required: true, message: '请输入事项名称' }],
  type_id: [{ required: true, message: '请选择事项类型' }],
  owner_id: [{ required: true, message: '请选择负责人' }],
}

let searchTimer: ReturnType<typeof setTimeout>

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchData, 300)
}

function handleSelectionChange(rows: any[]) {
  selectedIds.value = new Set(rows.map(r => r.id))
}

function cancelSelection() {
  clearSelection()
  tableRef.value?.clearSelection()
}

async function handleBatchAssign() {
  if (selectedIds.value.size === 0 || !assigneeId.value) return
  assigning.value = true
  try {
    const res = await post('/matters/batch/assign', {
      ids: Array.from(selectedIds.value),
      assignee_id: assigneeId.value,
    })
    ElMessage.success((res as any).detail || '批量分配成功')
    showAssignDialog.value = false
    assigneeId.value = null
    clearSelection()
    tableRef.value?.clearSelection()
    fetchData()
  } catch (e) {
    // Error handled by API interceptor
  } finally {
    assigning.value = false
  }
}

async function fetchData() {
  await matterStore.fetchMatters({
    page: page.value,
    page_size: pageSize.value,
    keyword: keyword.value || undefined,
    status: filterStatus.value || undefined,
    type_id: filterType.value || undefined,
    is_key_project: filterKeyProject.value || undefined,
  })
  setTotal(matterStore.total)
}

async function handleCreate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    await matterStore.createMatter({
      title: form.title,
      type_id: form.type_id,
      owner_id: form.owner_id,
      member_ids: form.member_ids,
      due_date: form.due_date?.toISOString(),
      workflow_template_id: form.workflow_template_id,
      is_key_project: form.is_key_project,
      description: form.description,
    })
    showCreate.value = false
    ElMessage.success('事项创建成功')
    await fetchData()
    resetForm()
  } finally {
    creating.value = false
  }
}

async function handleExport(command: string) {
  if (command === 'excel') {
    const token = localStorage.getItem('token')
    const response = await fetch('/api/v1/matters/export/excel', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `matters_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
  }
}

function resetForm() {
  form.title = ''
  form.type_id = null
  form.owner_id = null
  form.member_ids = []
  form.due_date = null
  form.workflow_template_id = null
  form.is_key_project = false
  form.description = ''
}

onMounted(async () => {
  loading.value = true
  await fetchData()
  loading.value = false
  // Load matter types, users, templates for create form
  usersApi.getList({ page_size: 200 }).then(r => userList.value = r.items)
  workflowApi.getTemplates({ page_size: 100 }).then(r => templates.value = r.items)
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-header h2 { margin: 0; }
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
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
.matter-title {
  display: flex;
  align-items: center;
  gap: 6px;
}
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>

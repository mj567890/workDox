<template>
  <div class="task-list-page">
    <div class="page-header">
      <h2>任务管理</h2>
      <el-button type="primary" @click="showCreate = true">从模板创建任务</el-button>
    </div>

    <el-table :data="store.tasks" v-loading="store.loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="title" label="任务名称" min-width="200" />
      <el-table-column label="模板" width="150">
        <template #default="{ row }">
          {{ row.template?.name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="current_stage_order" label="当前阶段" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="$router.push(`/task-mgmt/${row.id}`)">看板</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="从模板创建任务" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="模板">
          <el-select v-model="form.template_id" placeholder="选择模板" style="width: 100%">
            <el-option v-for="t in store.templates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务标题">
          <el-input v-model="form.title" placeholder="留空则使用模板名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useTaskMgmtStore } from '@/stores/task-mgmt'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useTaskMgmtStore()
const showCreate = ref(false)
const creating = ref(false)
const form = reactive({ template_id: 0, title: '' })

onMounted(async () => {
  await Promise.all([store.fetchTemplates(), store.fetchTasks()])
})

function statusTag(s: string) {
  const map: Record<string, string> = { pending: 'info', active: 'warning', completed: 'success', cancelled: 'danger' }
  return map[s] || 'info'
}

async function handleCreate() {
  if (!form.template_id) return
  creating.value = true
  try {
    await store.createTask({ template_id: form.template_id, title: form.title || undefined })
    ElMessage.success('任务创建成功')
    showCreate.value = false
    form.template_id = 0
    form.title = ''
  } catch {
    // interceptor handles error
  } finally {
    creating.value = false
  }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除任务「${row.title}」？`, '确认删除', { type: 'warning' })
    await store.deleteTask(row.id)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.task-list-page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; }
</style>

<template>
  <div class="template-list-page">
    <div class="page-header">
      <h2>任务模板管理</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>创建模板
      </el-button>
    </div>

    <el-table :data="store.templates" v-loading="store.loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="name" label="模板名称" min-width="180" />
      <el-table-column label="分类" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.category" size="small">{{ row.category }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="阶段数" width="80">
        <template #default="{ row }">{{ row.stages?.length || 0 }}</template>
      </el-table-column>
      <el-table-column label="系统模板" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.is_system" size="small" type="info">系统</el-tag>
          <el-tag v-else size="small" type="success">自定义</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button size="small" @click="$router.push(`/task-templates/${row.id}/edit`)">编辑</el-button>
          <el-button size="small" @click="handleClone(row)">克隆</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create Dialog -->
    <el-dialog v-model="showCreate" title="创建任务模板" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="模板名称">
          <el-input v-model="form.name" placeholder="如：合同审批流程" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="form.category" placeholder="如：采购、通用" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
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
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { useTaskMgmtStore } from '@/stores/task-mgmt'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useTaskMgmtStore()
const showCreate = ref(false)
const creating = ref(false)
const form = reactive({ name: '', category: '', description: '' })

onMounted(() => store.fetchTemplates())

function openCreate() {
  form.name = ''
  form.category = ''
  form.description = ''
  showCreate.value = true
}

async function handleCreate() {
  if (!form.name) return
  creating.value = true
  try {
    const tpl = await store.createTemplate({
      name: form.name,
      category: form.category || undefined,
      description: form.description || undefined,
    })
    showCreate.value = false
    ElMessage.success('模板创建成功')
  } catch {
    // handled by interceptor
  } finally {
    creating.value = false
  }
}

async function handleClone(row: any) {
  try {
    await ElMessageBox.confirm(`克隆模板「${row.name}」？将生成副本`, '确认克隆')
    const tpl = await store.cloneTemplate(row.id)
    ElMessage.success(`已克隆为「${tpl.name}」`)
  } catch { /* cancelled */ }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除模板「${row.name}」？`, '确认删除', { type: 'warning' })
    await store.deleteTemplate(row.id)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.template-list-page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; }
</style>

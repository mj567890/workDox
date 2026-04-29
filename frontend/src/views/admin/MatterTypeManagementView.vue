<template>
  <div class="matter-type-management">
    <div class="page-header">
      <h2>事项类型</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>创建事项类型
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="name" label="类型名称" width="180" />
        <el-table-column prop="code" label="类型代码" width="200" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showDialog" :title="isEdit ? '编辑事项类型' : '创建事项类型'" width="450px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="类型名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="类型代码" prop="code">
          <el-input v-model="form.code" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { usersApi, type MatterTypeItem } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const items = ref<MatterTypeItem[]>([])
const showDialog = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref()

const form = reactive({
  name: '',
  code: '',
  description: '',
})

const rules = {
  name: [{ required: true, message: '请输入类型名称' }],
  code: [{ required: true, message: '请输入类型代码' }],
}

async function fetchData() {
  loading.value = true
  try {
    items.value = await usersApi.getMatterTypes()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  form.name = ''
  form.code = ''
  form.description = ''
  showDialog.value = true
}

function openEdit(row: MatterTypeItem) {
  isEdit.value = true
  editingId.value = row.id
  form.name = row.name
  form.code = row.code
  form.description = row.description || ''
  showDialog.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value && editingId.value) {
      await usersApi.updateMatterType(editingId.value, { ...form })
      ElMessage.success('事项类型已更新')
    } else {
      await usersApi.createMatterType({ ...form })
      ElMessage.success('事项类型创建成功')
    }
    showDialog.value = false
    fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: MatterTypeItem) {
  try {
    await ElMessageBox.confirm(`确认删除事项类型 "${row.name}"？`, '确认')
    await usersApi.deleteMatterType(row.id)
    ElMessage.success('事项类型已删除')
    fetchData()
  } catch { /* cancelled */ }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
</style>

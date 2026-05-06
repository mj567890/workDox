<template>
  <div class="tag-management">
    <div class="page-header">
      <h2>标签管理</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>创建标签
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading" stripe>
        <template #empty>
          <el-empty description="暂无标签数据" />
        </template>
        <el-table-column label="颜色" width="80">
          <template #default="{ row }">
            <div :style="{ width: '24px', height: '24px', borderRadius: '4px', backgroundColor: row.color }" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="标签名称" width="200" />
        <el-table-column prop="color" label="颜色值" width="150" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showDialog" :title="isEdit ? '编辑标签' : '创建标签'" width="420px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标签名称" prop="name">
          <el-input v-model="form.name" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="颜色" prop="color">
          <el-color-picker v-model="form.color" show-alpha />
          <span style="margin-left: 8px; color: #999;">{{ form.color }}</span>
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
import { usersApi, type TagItem } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const items = ref<TagItem[]>([])
const showDialog = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref()

const form = reactive({
  name: '',
  color: '#409EFF',
})

const rules = {
  name: [{ required: true, message: '请输入标签名称' }],
  color: [{ required: true, message: '请选择颜色' }],
}

async function fetchData() {
  loading.value = true
  try {
    items.value = await usersApi.getTags()
  } finally {
    loading.value = false
  }
}

function openCreate() {
  isEdit.value = false
  editingId.value = null
  form.name = ''
  form.color = '#409EFF'
  showDialog.value = true
}

function openEdit(row: TagItem) {
  isEdit.value = true
  editingId.value = row.id
  form.name = row.name
  form.color = row.color
  showDialog.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value && editingId.value) {
      await usersApi.updateTag(editingId.value, { ...form })
      ElMessage.success('标签已更新')
    } else {
      await usersApi.createTag({ ...form })
      ElMessage.success('标签创建成功')
    }
    showDialog.value = false
    fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: TagItem) {
  try {
    await ElMessageBox.confirm(`确认删除标签 "${row.name}"？`, '确认')
    await usersApi.deleteTag(row.id)
    ElMessage.success('标签已删除')
    fetchData()
  } catch { /* cancelled */ }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
</style>

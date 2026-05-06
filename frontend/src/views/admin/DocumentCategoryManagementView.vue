<template>
  <div class="category-management">
    <div class="page-header">
      <h2>文档分类</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>创建分类
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="items" v-loading="loading" stripe>
        <template #empty>
          <el-empty description="暂无分类数据" />
        </template>
        <el-table-column prop="name" label="分类名称" width="180" />
        <el-table-column prop="code" label="分类代码" width="200" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column label="系统" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_system ? 'info' : ''" size="small">{{ row.is_system ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)" :disabled="row.is_system">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showDialog" :title="isEdit ? '编辑分类' : '创建分类'" width="450px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="form.name" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="分类代码" prop="code">
          <el-input v-model="form.code" :disabled="isEdit" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
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
import { usersApi, type DocumentCategoryItem } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const items = ref<DocumentCategoryItem[]>([])
const showDialog = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)
const formRef = ref()

const form = reactive({
  name: '',
  code: '',
  description: '',
  sort_order: 0,
})

const rules = {
  name: [{ required: true, message: '请输入分类名称' }],
  code: [{ required: true, message: '请输入分类代码' }],
}

async function fetchData() {
  loading.value = true
  try {
    items.value = await usersApi.getDocumentCategories()
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
  form.sort_order = 0
  showDialog.value = true
}

function openEdit(row: DocumentCategoryItem) {
  isEdit.value = true
  editingId.value = row.id
  form.name = row.name
  form.code = row.code
  form.description = row.description || ''
  form.sort_order = row.sort_order
  showDialog.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value && editingId.value) {
      await usersApi.updateDocumentCategory(editingId.value, { ...form })
      ElMessage.success('分类已更新')
    } else {
      await usersApi.createDocumentCategory({ ...form })
      ElMessage.success('分类创建成功')
    }
    showDialog.value = false
    fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: DocumentCategoryItem) {
  try {
    await ElMessageBox.confirm(`确认删除分类 "${row.name}"？`, '确认')
    await usersApi.deleteDocumentCategory(row.id)
    ElMessage.success('分类已删除')
    fetchData()
  } catch { /* cancelled */ }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
</style>

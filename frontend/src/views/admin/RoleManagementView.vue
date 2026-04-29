<template>
  <div class="role-management">
    <div class="page-header">
      <h2>角色管理</h2>
      <el-button type="primary" @click="showCreate = true">
        <el-icon><Plus /></el-icon>创建角色
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="roles" v-loading="loading" stripe>
        <el-table-column prop="role_name" label="角色名称" width="150" />
        <el-table-column prop="role_code" label="角色代码" width="200" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showCreate" title="创建角色" width="400px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="角色名称" prop="role_name">
          <el-input v-model="form.role_name" />
        </el-form-item>
        <el-form-item label="角色代码" prop="role_code">
          <el-input v-model="form.role_code" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { usersApi, type RoleItem } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'

const loading = ref(false)
const roles = ref<RoleItem[]>([])
const showCreate = ref(false)
const saving = ref(false)
const formRef = ref()

const form = reactive({
  role_name: '',
  role_code: '',
  description: '',
})

const rules = {
  role_name: [{ required: true, message: '请输入角色名称' }],
  role_code: [{ required: true, message: '请输入角色代码' }],
}

async function fetchData() {
  loading.value = true
  try {
    roles.value = await usersApi.getRoles()
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await usersApi.createRole({ ...form })
    showCreate.value = false
    ElMessage.success('角色创建成功')
    fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: RoleItem) {
  try {
    await ElMessageBox.confirm(`确认删除角色 "${row.role_name}"？`, '确认')
    await usersApi.deleteRole(row.id)
    ElMessage.success('角色已删除')
    fetchData()
  } catch { /* cancelled */ }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
</style>

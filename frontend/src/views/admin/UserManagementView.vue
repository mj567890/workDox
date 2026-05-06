<template>
  <div class="user-management">
    <div class="page-header">
      <h2>用户管理</h2>
      <el-button type="primary" @click="showCreate = true">
        <el-icon><Plus /></el-icon>创建用户
      </el-button>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="keyword" placeholder="搜索用户" clearable style="width: 200px" @input="fetchData" />
        <el-select v-model="filterDepartment" placeholder="部门" clearable @change="fetchData">
          <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
      </div>

      <el-table :data="users" v-loading="loading" stripe>
        <template #empty>
          <el-empty description="暂无用户数据" />
        </template>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="real_name" label="姓名" width="100" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="phone" label="电话" width="130" />
        <el-table-column prop="department_name" label="部门" width="120" />
        <el-table-column label="角色" width="200">
          <template #default="{ row }">
            <el-tag v-for="r in row.roles" :key="r.id" size="small" class="mr-4">{{ r.role_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">{{ row.status === 'active' ? '正常' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">禁用</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total"
          layout="total, sizes, prev, pager, next" @change="fetchData" />
      </div>
    </el-card>

    <el-dialog v-model="showCreate" :title="editingUser ? '编辑用户' : '创建用户'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!editingUser" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="密码" v-if="!editingUser">
          <el-input v-model="form.password" type="password" show-password maxlength="128" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="form.real_name" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" maxlength="20" show-word-limit />
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="form.department_id" clearable>
            <el-option v-for="d in departments" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple>
            <el-option v-for="r in roles" :key="r.id" :label="r.role_name" :value="r.id" />
          </el-select>
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
import { usersApi, type UserItem, type DepartmentItem, type RoleItem } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePagination } from '@/composables/usePagination'

const { page, pageSize, setTotal } = usePagination()
const loading = ref(false)
const users = ref<UserItem[]>([])
const total = ref(0)
const departments = ref<DepartmentItem[]>([])
const roles = ref<RoleItem[]>([])
const keyword = ref('')
const filterDepartment = ref<number | null>(null)

const showCreate = ref(false)
const editingUser = ref<UserItem | null>(null)
const saving = ref(false)
const formRef = ref()

const form = reactive({
  username: '',
  password: '',
  real_name: '',
  email: '',
  phone: '',
  department_id: null as number | null,
  role_ids: [] as number[],
})

const rules = {
  username: [{ required: true, message: '请输入用户名' }],
  real_name: [{ required: true, message: '请输入姓名' }],
}

let searchTimer: ReturnType<typeof setTimeout>

async function fetchData() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    loading.value = true
    try {
      const res = await usersApi.getList({
        page: page.value,
        page_size: pageSize.value,
        keyword: keyword.value || undefined,
        department_id: filterDepartment.value || undefined,
      })
      users.value = res.items
      total.value = res.total
      setTotal(res.total)
    } finally {
      loading.value = false
    }
  }, 200)
}

function handleEdit(row: UserItem) {
  editingUser.value = row
  form.username = row.username
  form.real_name = row.real_name
  form.email = row.email || ''
  form.phone = row.phone || ''
  form.department_id = row.department_id
  form.role_ids = row.roles.map(r => r.id)
  showCreate.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (editingUser.value) {
      await usersApi.update(editingUser.value.id, {
        real_name: form.real_name,
        email: form.email,
        phone: form.phone,
        department_id: form.department_id,
        role_ids: form.role_ids,
      })
    } else {
      await usersApi.create({ ...form })
    }
    showCreate.value = false
    editingUser.value = null
    ElMessage.success('保存成功')
    fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: UserItem) {
  try {
    await ElMessageBox.confirm(`确认禁用用户 "${row.real_name}"？`, '确认')
    await usersApi.delete(row.id)
    ElMessage.success('用户已禁用')
    fetchData()
  } catch { /* cancelled */ }
}

onMounted(async () => {
  await fetchData()
  try {
    const [deptRes, roleRes] = await Promise.all([
      usersApi.getDepartments(),
      usersApi.getRoles(),
    ])
    departments.value = deptRes
    roles.value = roleRes
  } catch {
    // Non-critical data; page still functions without departments/roles loaded
  }
})
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; }
.mr-4 { margin-right: 4px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>

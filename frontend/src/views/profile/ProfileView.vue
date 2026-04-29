<template>
  <div class="profile-view">
    <h2>个人资料</h2>

    <!-- 查看模式 -->
    <el-card v-if="!editing" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>基本信息</span>
          <el-button type="primary" @click="enterEdit">编辑资料</el-button>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="用户名">
          {{ user?.username || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="真实姓名">
          {{ user?.real_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="邮箱">
          {{ user?.email || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="手机号">
          {{ (user as any)?.phone || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="所属部门">
          {{ user?.department_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag
            v-for="role in user?.roles"
            :key="role.id"
            style="margin-right: 6px"
            type="info"
            size="small"
          >
            {{ role.role_name }}
          </el-tag>
          <span v-if="!user?.roles?.length">-</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 编辑模式 -->
    <el-card v-else v-loading="saving">
      <template #header>
        <div class="card-header">
          <span>编辑资料</span>
        </div>
      </template>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        style="max-width: 500px"
      >
        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model="form.real_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="所属部门" prop="department_id">
          <el-select
            v-model="form.department_id"
            placeholder="请选择部门"
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="dept in departments"
              :key="dept.id"
              :label="dept.name"
              :value="dept.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="submitForm">
            保存
          </el-button>
          <el-button @click="cancelEdit">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { type FormInstance, type FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { usersApi, type DepartmentItem } from '@/api/users'

const authStore = useAuthStore()
const user = authStore.user

const loading = ref(false)
const saving = ref(false)
const editing = ref(false)
const formRef = ref<FormInstance>()
const departments = ref<DepartmentItem[]>([])

const form = reactive({
  real_name: '',
  email: '',
  phone: '',
  department_id: null as number | null,
})

const rules: FormRules = {
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  email: [
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  phone: [
    {
      pattern: /^1[3-9]\d{9}$/,
      message: '请输入正确的手机号',
      trigger: 'blur',
    },
  ],
}

function enterEdit() {
  if (!user.value) return
  form.real_name = user.value.real_name
  form.email = user.value.email || ''
  form.phone = (user.value as any).phone || ''
  form.department_id = user.value.department_id
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function submitForm() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    await usersApi.update(user.value!.id, {
      real_name: form.real_name,
      email: form.email || null,
      phone: form.phone || null,
      department_id: form.department_id,
    })
    ElMessage.success('保存成功')
    editing.value = false
    await authStore.fetchUser()
  } catch (err: any) {
    const msg = err?.response?.data?.message || '保存失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

async function loadDepartments() {
  loading.value = true
  try {
    departments.value = await usersApi.getDepartments()
  } catch {
    departments.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDepartments()
})
</script>

<style scoped>
.profile-view {
  padding: 20px;
}

.profile-view h2 {
  margin: 0 0 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

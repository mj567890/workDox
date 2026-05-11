<template>
  <div class="reset-page">
    <div class="reset-card">
      <h2 class="reset-title">重置密码</h2>
      <p class="reset-subtitle">为您的账号设置新密码</p>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="handleSubmit">
        <el-form-item prop="new_password">
          <el-input v-model="form.new_password" type="password" placeholder="新密码" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" placeholder="确认新密码" :prefix-icon="Lock" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
            重置密码
          </el-button>
        </el-form-item>
      </el-form>

      <div class="back-link">
        <router-link to="/login">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Lock } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '@/api/auth'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const formRef = ref()

const token = route.query.token as string
if (!token) {
  ElMessage.error('无效的重置链接')
  router.push('/login')
}

const form = reactive({
  new_password: '',
  confirm_password: '',
})

const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码至少需要8个字符', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authApi.resetPassword(token, form.new_password)
    ElMessage.success('密码重置成功')
    router.push('/login')
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '重置失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.reset-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.reset-card {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}
.reset-title {
  text-align: center;
  margin: 0 0 8px;
  color: #303133;
}
.reset-subtitle {
  text-align: center;
  color: #909399;
  margin: 0 0 24px;
  font-size: 13px;
}
.back-link {
  text-align: center;
  margin-top: 12px;
}
.back-link a {
  color: #409eff;
  font-size: 13px;
  text-decoration: none;
}
.back-link a:hover {
  text-decoration: underline;
}
</style>

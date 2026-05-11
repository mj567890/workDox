<template>
  <div class="forgot-page">
    <div class="forgot-card">
      <h2 class="forgot-title">忘记密码</h2>
      <p class="forgot-subtitle">输入您的注册邮箱，我们将发送密码重置链接</p>

      <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="handleSubmit">
        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="注册邮箱" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
            发送重置链接
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
import { User } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const formRef = ref()
const form = reactive({ email: '' })
const rules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await authApi.forgotPassword(form.email)
    ElMessage.success('如果该邮箱已注册，重置链接已发送')
    router.push('/login')
  } catch (err: any) {
    const detail = err?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '发送失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.forgot-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.forgot-card {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}
.forgot-title {
  text-align: center;
  margin: 0 0 8px;
  color: #303133;
}
.forgot-subtitle {
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

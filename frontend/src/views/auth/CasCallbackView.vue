<template>
  <div class="callback-page">
    <el-result v-if="error" icon="error" title="登录失败" :sub-title="error">
      <template #extra>
        <el-button type="primary" @click="$router.push('/login')">返回登录</el-button>
      </template>
    </el-result>
    <div v-else class="loading">
      <el-icon class="is-loading" :size="48"><Loading /></el-icon>
      <p>正在通过统一认证登录...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Loading } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const error = ref('')

onMounted(async () => {
  const token = (route.query.token as string) || ''
  if (!token) {
    const err = route.query.error as string
    error.value = err || '缺少认证令牌'
    return
  }

  localStorage.setItem('token', token)
  try {
    await authStore.fetchUser()
    router.push('/')
  } catch {
    error.value = '获取用户信息失败'
    localStorage.removeItem('token')
  }
})
</script>

<style scoped>
.callback-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.loading {
  text-align: center;
  color: #909399;
}
.loading p {
  margin-top: 16px;
}
</style>

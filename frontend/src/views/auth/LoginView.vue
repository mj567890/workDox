<template>
  <div class="login-page">
    <div class="login-card">
      <h2 class="login-title">WorkDox</h2>
      <p class="login-subtitle">让文档真正干活的协同工作平台</p>

      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="密码登录" name="local">
          <el-form ref="formRef" :model="form" :rules="rules" size="large" @submit.prevent="handleLogin('local')">
            <el-form-item prop="username">
              <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="Lock" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
                登 录
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane v-if="providers.includes('ldap')" label="LDAP 登录" name="ldap">
          <el-form ref="ldapFormRef" :model="form" :rules="rules" size="large" @submit.prevent="handleLogin('ldap')">
            <el-form-item prop="username">
              <el-input v-model="form.username" placeholder="域账号" :prefix-icon="User" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="form.password" type="password" placeholder="域密码" :prefix-icon="Lock" show-password />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">
                LDAP 登录
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <div v-if="oauth2Providers.length > 0" class="sso-section">
        <el-divider>第三方登录</el-divider>
        <div class="sso-buttons">
          <el-button
            v-for="p in oauth2Providers"
            :key="p.name"
            size="large"
            class="sso-btn"
            @click="handleSSOLogin"
          >
            {{ p.name }} 登录
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi, type ProvidersResponse } from '@/api/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const formRef = ref()
const activeTab = ref('local')
const providers = ref<string[]>([])
const oauth2Providers = ref<{ name: string; type: string }[]>([])

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

onMounted(async () => {
  try {
    const res = await authApi.getProviders()
    providers.value = res.providers.filter((p): p is string => typeof p === 'string')
    oauth2Providers.value = res.providers.filter(
      (p): p is { name: string; type: string } => typeof p !== 'string'
    ) as { name: string; type: string }[]
  } catch {
    // Default to local-only
  }
})

async function handleLogin(mode: string) {
  const refEl = mode === 'ldap' ? formRef.value : formRef.value
  const valid = await refEl?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    if (mode === 'ldap') {
      await authStore.ldapLogin(form.username, form.password)
    } else {
      await authStore.login(form.username, form.password)
    }
    ElMessage.success('登录成功')
    router.push('/')
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

function handleSSOLogin() {
  window.location.href = authApi.getOAuth2AuthorizeUrl()
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 420px;
  padding: 40px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}
.login-title {
  text-align: center;
  margin: 0 0 8px;
  color: #303133;
}
.login-subtitle {
  text-align: center;
  color: #909399;
  margin: 0 0 24px;
  font-size: 13px;
}
.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 8px;
}
.sso-section {
  margin-top: 4px;
}
.sso-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}
.sso-btn {
  flex: 1;
}
</style>

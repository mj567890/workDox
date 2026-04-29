<template>
  <div class="settings-view">
    <h2>账号设置</h2>

    <!-- 修改密码 -->
    <el-card class="settings-card" v-loading="changingPassword">
      <template #header>
        <span>修改密码</span>
      </template>
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-width="100px"
        style="max-width: 450px"
      >
        <el-form-item label="当前密码" prop="old_password">
          <el-input
            v-model="passwordForm.old_password"
            type="password"
            show-password
            placeholder="请输入当前密码"
          />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input
            v-model="passwordForm.new_password"
            type="password"
            show-password
            placeholder="请输入新密码"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input
            v-model="passwordForm.confirm_password"
            type="password"
            show-password
            placeholder="请再次输入新密码"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="changingPassword" @click="changePassword">
            修改密码
          </el-button>
          <el-button @click="resetPasswordForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 通知设置 -->
    <el-card class="settings-card">
      <template #header>
        <span>通知设置</span>
      </template>
      <div class="notification-settings">
        <div class="setting-item">
          <div class="setting-label">
            <span class="setting-title">页面内通知</span>
            <span class="setting-desc">在系统页面内展示通知消息</span>
          </div>
          <el-switch v-model="notificationSettings.inApp" />
        </div>
        <el-divider />
        <div class="setting-item">
          <div class="setting-label">
            <span class="setting-title">邮件通知</span>
            <span class="setting-desc">通过邮件接收重要事项提醒，发送到：{{ authStore.user?.email || '未设置邮箱' }}</span>
          </div>
          <el-switch v-model="notificationSettings.email" />
        </div>
        <el-divider />
        <div class="setting-item">
          <div class="setting-label">
            <span class="setting-title">待办提醒</span>
            <span class="setting-desc">待办任务到期前发送提醒通知</span>
          </div>
          <el-switch v-model="notificationSettings.taskReminder" />
        </div>
        <el-divider />
        <div class="setting-item">
          <div class="setting-label">
            <span class="setting-title">事项状态变更通知</span>
            <span class="setting-desc">关注的事项状态发生变更时通知</span>
          </div>
          <el-switch v-model="notificationSettings.matterUpdate" />
        </div>
      </div>
      <div class="notification-tip">
        <el-alert
          title="提示：通知设置为前端 UI 预览，暂未与后端存储联动。"
          type="info"
          :closable="false"
          show-icon
        />
      </div>
    </el-card>

    <!-- Webhook 管理入口 -->
    <el-card class="settings-card">
      <template #header>
        <span>集成与 API</span>
      </template>
      <div class="integration-links">
        <div class="integration-item" @click="$router.push('/webhooks')">
          <div class="integration-left">
            <div class="integration-title">Webhook 管理</div>
            <div class="integration-desc">配置事件推送，将系统事件推送到外部服务</div>
          </div>
          <el-button text type="primary">管理</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { type FormInstance, type FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { usersApi } from '@/api/users'

const authStore = useAuthStore()

// ---------- 密码修改 ----------
const passwordFormRef = ref<FormInstance>()
const changingPassword = ref(false)

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const validateConfirmPassword = (_rule: any, value: string, callback: Function) => {
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules: FormRules = {
  old_password: [
    { required: true, message: '请输入当前密码', trigger: 'blur' },
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于 6 位', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

async function changePassword() {
  if (!passwordFormRef.value) return
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return

  changingPassword.value = true
  try {
    await usersApi.changePassword(authStore.user!.id, {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
    })
    ElMessage.success('密码修改成功')
    resetPasswordForm()
  } catch (err: any) {
    const msg = err?.response?.data?.message || '密码修改失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    changingPassword.value = false
  }
}

function resetPasswordForm() {
  if (passwordFormRef.value) {
    passwordFormRef.value.resetFields()
  }
}

// ---------- 通知设置（仅 UI）----------
const notificationSettings = reactive({
  inApp: true,
  email: true,
  taskReminder: true,
  matterUpdate: false,
})
</script>

<style scoped>
.settings-view {
  padding: 20px;
}

.settings-view h2 {
  margin: 0 0 20px;
}

.settings-card {
  margin-bottom: 20px;
}

.notification-settings {
  max-width: 500px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
}

.setting-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.setting-title {
  font-size: 14px;
  font-weight: 500;
}

.setting-desc {
  font-size: 12px;
  color: #909399;
}

.notification-tip {
  max-width: 500px;
  margin-top: 16px;
}

.integration-links {
  max-width: 500px;
}

.integration-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.3s;
}

.integration-item:hover {
  border-color: #409EFF;
}

.integration-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.integration-title {
  font-size: 14px;
  font-weight: 500;
}

.integration-desc {
  font-size: 12px;
  color: #909399;
}
</style>

<template>
  <div class="webhook-management">
    <el-page-header @back="$router.back()">
      <template #content><span class="page-title">Webhook 管理</span></template>
    </el-page-header>

    <el-alert
      title="Webhook 用于将系统事件推送到外部服务。系统会使用 HMAC-SHA256 对推送内容签名。"
      type="info" :closable="false" class="mt-16 mb-16"
    />

    <el-card shadow="never">
      <div class="toolbar mb-16">
        <span class="text-gray">支持的事件类型：</span>
        <el-tag size="small" v-for="evt in eventTypes" :key="evt" class="ml-4">{{ evt }}</el-tag>
        <el-button type="primary" class="ml-16" @click="showCreate = true">创建 Webhook</el-button>
      </div>

      <el-table :data="webhooks" stripe v-loading="loading">
        <template #empty>
          <el-empty description="暂无 Webhook 配置" />
        </template>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="url" label="URL" min-width="250" show-overflow-tooltip />
        <el-table-column label="事件" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="evt in (row.events || '').split(',')" :key="evt" size="small" class="mr-4">
              {{ evt }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近触发" width="180">
          <template #default="{ row }">
            <div v-if="row.last_triggered_at">
              <div>{{ formatDate(row.last_triggered_at) }}</div>
              <el-tag :type="row.last_status === 'success' ? 'success' : 'danger'" size="small">
                {{ row.last_status }}
              </el-tag>
            </div>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="editWebhook(row)">编辑</el-button>
            <el-button text type="warning" size="small" @click="handleRegenerate(row.id)">重置密钥</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog v-model="showCreate" :title="editingId ? '编辑 Webhook' : '创建 Webhook'" width="550px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="例如：钉钉通知" />
        </el-form-item>
        <el-form-item label="URL" required>
          <el-input v-model="form.url" placeholder="https://your-server.com/webhook" />
        </el-form-item>
        <el-form-item label="事件" required>
          <el-checkbox-group v-model="form.events">
            <el-checkbox v-for="evt in eventTypes" :key="evt" :label="evt" :value="evt">
              {{ evt }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ editingId ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { get, post, put, del } from '@/api'
import { formatDate } from '@/utils/format'

interface WebhookItem {
  id: number
  name: string
  url: string
  events: string
  is_active: boolean
  last_triggered_at: string | null
  last_status: string | null
  created_at: string | null
}

const eventTypes = [
  'document.uploaded', 'document.approved', 'document.rejected',
  'task.assigned', 'task.completed',
  'notification.created',
]

const loading = ref(false)
const webhooks = ref<WebhookItem[]>([])
const showCreate = ref(false)
const editingId = ref<number | null>(null)
const saving = ref(false)

const form = ref({
  name: '',
  url: '',
  events: [] as string[],
  is_active: true,
})

function resetForm() {
  form.value = { name: '', url: '', events: [], is_active: true }
  editingId.value = null
}

function editWebhook(row: WebhookItem) {
  editingId.value = row.id
  form.value = {
    name: row.name,
    url: row.url,
    events: (row.events || '').split(',').filter(Boolean),
    is_active: row.is_active,
  }
  showCreate.value = true
}

async function loadData() {
  loading.value = true
  try {
    const res = await get<{ items: WebhookItem[] }>('/webhooks', { page_size: 100 })
    webhooks.value = res.items || []
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!form.value.name || !form.value.url || form.value.events.length === 0) {
    ElMessage.warning('请填写完整信息')
    return
  }
  saving.value = true
  try {
    if (editingId.value) {
      await put(`/webhooks/${editingId.value}`, form.value)
      ElMessage.success('已更新')
    } else {
      await post('/webhooks', form.value)
      ElMessage.success('已创建')
    }
    showCreate.value = false
    resetForm()
    await loadData()
  } finally {
    saving.value = false
  }
}

async function handleRegenerate(id: number) {
  try {
    await ElMessageBox.confirm('重置密钥后，旧的签名将失效。确认？', '重置密钥')
    const res = await post<{ secret: string }>(`/webhooks/${id}/regenerate-secret`)
    ElMessage.success(`新密钥: ${res.secret}`)
  } catch { /* cancelled */ }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确认删除此 Webhook？', '删除确认', { type: 'warning' })
    await del(`/webhooks/${id}`)
    ElMessage.success('已删除')
    await loadData()
  } catch { /* cancelled */ }
}

onMounted(loadData)
</script>

<style scoped>
.webhook-management { padding: 0; }
.page-title { font-size: 18px; font-weight: 600; }
.mt-16 { margin-top: 16px; }
.mb-16 { margin-bottom: 16px; }
.ml-4 { margin-left: 4px; }
.ml-16 { margin-left: 16px; }
.mr-4 { margin-right: 4px; }
.text-gray { color: #999; }
.toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
</style>

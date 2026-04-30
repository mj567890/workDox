<template>
  <div class="ai-config-page">
    <h2>AI 配置管理</h2>
    <p class="page-desc">管理多个 AI 供应商，可在 AI 助手中自由切换使用。</p>

    <!-- Provider Table -->
    <el-card shadow="never" style="margin-bottom: 20px">
      <template #header>
        <div class="card-header">
          <span>AI 供应商</span>
          <el-button type="primary" size="small" @click="openCreate">添加供应商</el-button>
        </div>
      </template>

      <el-table :data="providers" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.provider_type)" size="small">
              {{ typeLabel(row.provider_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="model" label="模型" min-width="160" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_enabled"
              @change="(val: boolean) => toggleProvider(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="60" />
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- RAG Panel -->
    <el-card shadow="never">
      <template #header>
        <span>RAG 检索参数</span>
      </template>
      <el-form :model="ragForm" label-width="140px" label-position="right" size="default">
        <el-form-item v-for="item in ragFields" :key="item.key" :label="item.label">
          <el-input-number v-model="ragForm[item.key]" :min="item.min || 1" style="width: 200px" />
          <div class="field-hint">{{ item.hint }}</div>
        </el-form-item>
        <el-form-item label="默认供应商">
          <el-select
            v-model="ragForm['ai.default_provider_id']"
            placeholder="自动选择"
            clearable
            style="width: 260px"
          >
            <el-option
              v-for="p in providers"
              :key="p.id"
              :label="`${p.name} (${p.model})`"
              :value="String(p.id)"
            />
          </el-select>
          <div class="field-hint">AI 助手未选择供应商时使用的默认模型</div>
        </el-form-item>
      </el-form>
      <div style="margin-top: 16px; text-align: right">
        <el-button type="primary" :loading="savingRag" @click="handleSaveRag">保存 RAG 参数</el-button>
      </div>
    </el-card>

    <!-- Create / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingProvider ? '编辑供应商' : '添加供应商'"
      width="560px"
      destroy-on-close
    >
      <el-form :model="form" label-width="120px" label-position="right">
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="如 DeepSeek V3" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.provider_type" style="width: 100%">
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="通义千问" value="qwen" />
            <el-option label="OpenAI" value="openai" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="API 地址">
          <el-input v-model="form.api_base" placeholder="https://api.deepseek.com/v1" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="form.api_key" type="password" show-password placeholder="sk-..." />
        </el-form-item>
        <el-form-item label="模型名称">
          <el-input v-model="form.model" placeholder="deepseek-chat" />
        </el-form-item>
        <el-form-item label="最大 Token 数">
          <el-input-number v-model="form.max_tokens" :min="256" :max="131072" style="width: 200px" />
        </el-form-item>
        <el-form-item label="温度">
          <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" :precision="1" style="width: 200px" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" style="width: 200px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { systemApi, type AIProvider, type ProviderCreate } from '@/api/system'

const loading = ref(true)
const saving = ref(false)
const savingRag = ref(false)
const providers = ref<AIProvider[]>([])
const dialogVisible = ref(false)
const editingProvider = ref<AIProvider | null>(null)

const defaultForm = () => ({
  name: '',
  provider_type: 'custom',
  api_base: '',
  api_key: '',
  model: '',
  max_tokens: 4096,
  temperature: 0.3,
  sort_order: 0,
})

const form = reactive(defaultForm())

const ragForm = reactive<Record<string, any>>({
  'ai.rag_top_k': 5,
  'ai.rag_chunk_size': 500,
  'ai.rag_chunk_overlap': 50,
  'ai.default_provider_id': '',
})

const ragFields = [
  { key: 'ai.rag_top_k', label: '检索片段数', min: 1, hint: '每次查询返回最相似的文档片段数' },
  { key: 'ai.rag_chunk_size', label: '文档分块大小', min: 100, hint: '文档切片时的每块字符数' },
  { key: 'ai.rag_chunk_overlap', label: '分块重叠大小', min: 0, hint: '相邻块之间的重叠字符数' },
]

function typeTag(t: string) {
  const map: Record<string, string> = { deepseek: '', qwen: 'success', openai: 'warning', custom: 'info' }
  return map[t] || 'info'
}

function typeLabel(t: string) {
  const map: Record<string, string> = { deepseek: 'DeepSeek', qwen: '千问', openai: 'OpenAI', custom: '自定义' }
  return map[t] || t
}

async function fetchProviders() {
  providers.value = await systemApi.getProviders()
}

async function fetchRagConfig() {
  try {
    const res = await systemApi.getAIConfig()
    for (const item of res.items) {
      if (item.key in ragForm) {
        ragForm[item.key] = item.value
      }
    }
  } catch { /* ignore */ }
}

async function toggleProvider(row: AIProvider, val: boolean) {
  await systemApi.updateProvider(row.id, { is_enabled: val })
  row.is_enabled = val
  ElMessage.success(val ? '已启用' : '已禁用')
}

function openCreate() {
  editingProvider.value = null
  Object.assign(form, defaultForm())
  dialogVisible.value = true
}

function openEdit(row: AIProvider) {
  editingProvider.value = row
  form.name = row.name
  form.provider_type = row.provider_type
  form.api_base = row.api_base
  form.api_key = row.api_key
  form.model = row.model
  form.max_tokens = row.max_tokens
  form.temperature = row.temperature
  form.sort_order = row.sort_order
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const data: ProviderCreate = {
      name: form.name,
      provider_type: form.provider_type,
      api_base: form.api_base,
      api_key: form.api_key,
      model: form.model,
      max_tokens: form.max_tokens,
      temperature: form.temperature,
      sort_order: form.sort_order,
    }
    if (editingProvider.value) {
      await systemApi.updateProvider(editingProvider.value.id, data)
      ElMessage.success('已更新')
    } else {
      await systemApi.createProvider(data)
      ElMessage.success('已添加')
    }
    dialogVisible.value = false
    await fetchProviders()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: AIProvider) {
  try {
    await ElMessageBox.confirm(`确定删除供应商 "${row.name}"？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await systemApi.deleteProvider(row.id)
    ElMessage.success('已删除')
    await fetchProviders()
  } catch { /* cancelled */ }
}

async function handleSaveRag() {
  savingRag.value = true
  try {
    const items = Object.entries(ragForm).map(([key, value]) => ({
      key,
      value: String(value),
      description: null,
    }))
    await systemApi.updateAIConfig(items)
    ElMessage.success('RAG 参数已保存')
  } finally {
    savingRag.value = false
  }
}

onMounted(async () => {
  try {
    await Promise.all([fetchProviders(), fetchRagConfig()])
  } catch {
    // API errors already handled by axios interceptor
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.ai-config-page { padding: 20px; max-width: 1000px; }
.ai-config-page h2 { margin: 0 0 8px; }
.page-desc { color: #909399; margin: 0 0 20px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.field-hint { font-size: 12px; color: #c0c4cc; margin-top: 4px; }
</style>

<template>
  <div class="workflow-templates">
    <div class="page-header">
      <h2>流程模板管理</h2>
      <el-button type="primary" @click="showCreate = true" v-if="isAdmin">
        <el-icon><Plus /></el-icon>创建模板
      </el-button>
    </div>

    <el-card shadow="never">
      <el-table :data="templates" v-loading="loading" stripe>
        <el-table-column prop="name" label="模板名称" min-width="200" />
        <el-table-column prop="matter_type_name" label="适用事项类型" width="150" />
        <el-table-column prop="node_count" label="节点数" width="80" />
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150" />
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="160" v-if="isAdmin">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="viewTemplate(row)">查看</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @change="fetchData"
        />
      </div>
    </el-card>

    <el-dialog v-model="showCreate" title="创建流程模板" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="模板名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="事项类型">
          <el-select v-model="form.matter_type_id" placeholder="选择类型">
            <el-option v-for="t in matterTypes" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="流程节点">
          <div class="node-list">
            <div v-for="(node, index) in form.nodes" :key="index" class="node-row">
              <el-input v-model="node.node_name" placeholder="节点名称" style="width: 150px" />
              <el-select v-model="node.owner_role" placeholder="负责角色" style="width: 130px">
                <el-option label="事项负责人" value="matter_owner" />
                <el-option label="部门领导" value="dept_leader" />
                <el-option label="普通员工" value="general_staff" />
              </el-select>
              <el-input-number v-model="node.sla_hours" :min="0" placeholder="SLA(h)" style="width: 100px" controls-position="right" />
              <el-button text type="danger" @click="form.nodes.splice(index, 1)">删除</el-button>
            </div>
            <el-button text type="primary" @click="form.nodes.push({ node_name: '', node_order: form.nodes.length + 1, owner_role: 'matter_owner', sla_hours: null })">
              + 添加节点
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDetail" title="模板详情" width="600px">
      <el-timeline>
        <el-timeline-item v-for="(node, index) in detailNodes" :key="index" :timestamp="`节点 ${index + 1}`" placement="top">
          <strong>{{ node.node_name }}</strong>
          <p>负责角色: {{ node.owner_role }}</p>
          <p v-if="node.sla_hours != null">SLA 时限: {{ node.sla_hours }} 小时</p>
          <p v-if="node.description">{{ node.description }}</p>
          <div v-if="node.required_documents_rule">
            <p>必需文档规则: {{ JSON.stringify(node.required_documents_rule) }}</p>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { workflowApi, type WorkflowTemplateItem, type TemplateNodeItem } from '@/api/workflow'
import { usePagination } from '@/composables/usePagination'
import { formatDate } from '@/utils/format'
import { ElMessage, ElMessageBox } from 'element-plus'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.isAdmin)

const { page, pageSize, setTotal } = usePagination()
const loading = ref(false)
const templates = ref<WorkflowTemplateItem[]>([])
const total = ref(0)
const matterTypes = ref<any[]>([])

const showCreate = ref(false)
const creating = ref(false)
const form = reactive({
  name: '',
  matter_type_id: null as number | null,
  description: '',
  nodes: [{ node_name: '', node_order: 1, owner_role: 'matter_owner' }],
})

const showDetail = ref(false)
const detailNodes = ref<TemplateNodeItem[]>([])

async function fetchData() {
  loading.value = true
  try {
    const res = await workflowApi.getTemplates({ page: page.value, page_size: pageSize.value })
    templates.value = res.items
    total.value = res.total
    setTotal(res.total)
  } finally {
    loading.value = false
  }
}

async function viewTemplate(row: WorkflowTemplateItem) {
  const res = await workflowApi.getTemplateDetail(row.id)
  detailNodes.value = res.nodes
  showDetail.value = true
}

async function handleCreate() {
  creating.value = true
  try {
    await workflowApi.createTemplate({
      name: form.name,
      matter_type_id: form.matter_type_id,
      description: form.description,
      nodes: form.nodes,
    })
    showCreate.value = false
    ElMessage.success('模板创建成功')
    fetchData()
  } finally {
    creating.value = false
  }
}

async function handleDelete(id: number) {
  try {
    await ElMessageBox.confirm('确认删除此模板？', '确认')
    await workflowApi.deleteTemplate(id)
    ElMessage.success('删除成功')
    fetchData()
  } catch { /* cancelled */ }
}

onMounted(fetchData)
</script>

<style scoped>
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
.node-list { width: 100%; }
.node-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
</style>

<template>
  <div class="template-edit" v-loading="loading">
    <el-page-header @back="$router.push('/workflow/templates')">
      <template #content>
        <span class="page-title">{{ isEdit ? '编辑流程模板' : '新建流程模板' }}</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" class="mt-20">
      <el-col :span="16">
        <!-- 基本信息 -->
        <el-card header="基本信息" shadow="never">
          <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
            <el-form-item label="模板名称" prop="name">
              <el-input v-model="form.name" placeholder="请输入模板名称" />
            </el-form-item>
            <el-form-item label="事项类型" prop="matter_type_id">
              <el-select v-model="form.matter_type_id" placeholder="请选择事项类型" style="width: 100%">
                <el-option v-for="t in matterTypes" :key="t.id" :label="t.name" :value="t.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="描述">
              <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入模板描述" />
            </el-form-item>
            <el-form-item label="启用状态">
              <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 节点管理 -->
        <el-card header="流程节点" shadow="never" class="mt-20">
          <template #header>
            <div class="card-header">
              <span>流程节点</span>
              <el-button type="primary" size="small" @click="showAddNode = true">
                <el-icon><Plus /></el-icon>添加节点
              </el-button>
            </div>
          </template>

          <el-table :data="form.nodes" stripe border>
            <el-table-column label="序号" type="index" width="60" />
            <el-table-column prop="node_name" label="节点名称" min-width="160">
              <template #default="{ row }">
                <span :class="{ 'text-danger': !row.node_name }">{{ row.node_name || '(未填写)' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="owner_role" label="负责角色" width="150">
              <template #default="{ row }">
                <el-tag size="small">{{ getRoleLabel(row.owner_role) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="sla_hours" label="SLA(H)" width="90">
              <template #default="{ row }">
                {{ row.sla_hours != null ? row.sla_hours + 'h' : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="150">
              <template #default="{ row }">
                {{ row.description || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ $index }">
                <el-button text type="primary" size="small" :disabled="$index === 0" @click="moveNode($index, -1)">
                  <el-icon><Top /></el-icon>
                </el-button>
                <el-button text type="primary" size="small" :disabled="$index === form.nodes.length - 1" @click="moveNode($index, 1)">
                  <el-icon><Bottom /></el-icon>
                </el-button>
                <el-button text type="danger" size="small" @click="removeNode($index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div v-if="form.nodes.length === 0" class="empty-tip">暂无节点，请点击"添加节点"按钮添加流程节点</div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never">
          <template #header>
            <span>操作</span>
          </template>
          <div class="actions-side">
            <el-button type="primary" size="large" :loading="saving" @click="handleSave" style="width: 100%">
              {{ isEdit ? '保存修改' : '创建模板' }}
            </el-button>
            <el-button size="large" @click="$router.push('/workflow/templates')" style="width: 100%; margin-top: 10px">
              取消
            </el-button>
            <el-divider />
            <div class="tips">
              <p class="tip-title">提示</p>
              <ul>
                <li>节点将按列表顺序执行</li>
                <li>可通过上下箭头调整节点顺序</li>
                <li>每个节点需要指定负责角色</li>
                <li>至少需要一个流程节点</li>
              </ul>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 添加节点对话框 -->
    <el-dialog v-model="showAddNode" title="添加流程节点" width="500px" :close-on-click-modal="false">
      <el-form :model="nodeForm" ref="nodeFormRef" :rules="nodeRules" label-width="90px">
        <el-form-item label="节点名称" prop="node_name">
          <el-input v-model="nodeForm.node_name" placeholder="如：初审、复审、终审" />
        </el-form-item>
        <el-form-item label="负责角色" prop="owner_role">
          <el-select v-model="nodeForm.owner_role" placeholder="选择负责角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.role_code" :label="r.role_name" :value="r.role_code" />
          </el-select>
        </el-form-item>
        <el-form-item label="SLA 时限">
          <el-input-number
            v-model="nodeForm.sla_hours"
            :min="0"
            :step="1"
            placeholder="小时数（留空表示无时限）"
            style="width: 100%"
            controls-position="right"
          />
          <div class="form-tip">设置该节点的 SLA 处理时限，单位为小时</div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="nodeForm.description" type="textarea" :rows="2" placeholder="节点说明（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddNode = false">取消</el-button>
        <el-button type="primary" @click="handleAddNode">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, Top, Bottom, Delete } from '@element-plus/icons-vue'
import { workflowApi, type WorkflowTemplateItem, type TemplateNodeItem } from '@/api/workflow'
import { usersApi, type RoleItem } from '@/api/users'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => route.name === 'WorkflowTemplateEdit')

const loading = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()
const nodeFormRef = ref<FormInstance>()

const roles = ref<RoleItem[]>([])

// 事项类型选项
const matterTypes = [
  { id: 1, name: '行政许可' },
  { id: 2, name: '行政处罚' },
  { id: 3, name: '行政确认' },
  { id: 4, name: '行政裁决' },
  { id: 5, name: '其他事项' },
]

// 节点数据接口
interface NodeFormItem {
  node_name: string
  owner_role: string
  sla_hours: number | null
  description: string
}

// 主表单
const form = reactive({
  name: '',
  matter_type_id: null as number | null,
  description: '',
  is_active: true,
  nodes: [] as NodeFormItem[],
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  matter_type_id: [{ required: true, message: '请选择事项类型', trigger: 'change' }],
}

// 节点对话框
const showAddNode = ref(false)
const nodeForm = reactive<NodeFormItem>({
  node_name: '',
  owner_role: '',
  sla_hours: null,
  description: '',
})

const nodeRules: FormRules = {
  node_name: [{ required: true, message: '请输入节点名称', trigger: 'blur' }],
  owner_role: [{ required: true, message: '请选择负责角色', trigger: 'change' }],
}

function getRoleLabel(code: string): string {
  const found = roles.value.find(r => r.role_code === code)
  return found ? found.role_name : code
}

function handleAddNode() {
  nodeFormRef.value?.validate((valid) => {
    if (!valid) return
    form.nodes.push({
      node_name: nodeForm.node_name.trim(),
      owner_role: nodeForm.owner_role,
      sla_hours: nodeForm.sla_hours,
      description: nodeForm.description.trim(),
    })
    nodeForm.node_name = ''
    nodeForm.owner_role = ''
    nodeForm.sla_hours = null
    nodeForm.description = ''
    showAddNode.value = false
  })
}

function removeNode(index: number) {
  form.nodes.splice(index, 1)
}

function moveNode(index: number, direction: number) {
  const target = index + direction
  if (target < 0 || target >= form.nodes.length) return
  const temp = form.nodes[index]
  form.nodes[index] = form.nodes[target]
  form.nodes[target] = temp
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  if (form.nodes.length === 0) {
    ElMessage.warning('请至少添加一个流程节点')
    return
  }

  saving.value = true
  try {
    const payload = {
      name: form.name,
      matter_type_id: form.matter_type_id,
      description: form.description || null,
      is_active: form.is_active,
      nodes: form.nodes.map((node, index) => ({
        node_name: node.node_name,
        node_order: index + 1,
        owner_role: node.owner_role,
        sla_hours: node.sla_hours,
        description: node.description || null,
      })),
    }

    if (isEdit.value) {
      const id = Number(route.params.id)
      await workflowApi.updateTemplate(id, payload)
      ElMessage.success('模板更新成功')
    } else {
      await workflowApi.createTemplate(payload)
      ElMessage.success('模板创建成功')
    }

    router.push('/workflow/templates')
  } finally {
    saving.value = false
  }
}

async function loadData() {
  loading.value = true
  try {
    if (isEdit.value) {
      const id = Number(route.params.id)
      const res = await workflowApi.getTemplateDetail(id)
      form.name = res.template.name
      form.matter_type_id = res.template.matter_type_id
      form.description = res.template.description || ''
      form.is_active = res.template.is_active
      form.nodes = res.nodes.map((node: TemplateNodeItem) => ({
        node_name: node.node_name,
        owner_role: node.owner_role,
        sla_hours: node.sla_hours,
        description: node.description || '',
      }))
    }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    roles.value = await usersApi.getRoles()
  } catch {
    // 角色加载失败不影响主流程
  }
  loadData()
})
</script>

<style scoped>
.page-title {
  font-size: 18px;
  font-weight: 600;
}

.mt-20 {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text-danger {
  color: #f56c6c;
}

.empty-tip {
  padding: 24px 0;
  text-align: center;
  color: #999;
  font-size: 13px;
}

.actions-side {
  padding: 0 4px;
}

.tips {
  font-size: 13px;
  color: #666;
}

.form-tip {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.tip-title {
  font-weight: 600;
  margin-bottom: 8px;
}

.tips ul {
  padding-left: 18px;
  margin: 0;
}

.tips li {
  margin-bottom: 4px;
  line-height: 1.6;
}
</style>

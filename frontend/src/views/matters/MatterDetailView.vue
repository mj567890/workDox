<template>
  <div class="matter-detail" v-loading="loading">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="page-title">{{ matter?.title }}</span>
      </template>
      <template #extra>
        <el-tag v-if="matter?.is_key_project" type="danger" effect="dark">重点工作</el-tag>
        <StatusTag v-if="matter" :status="matter.status" type="matter" class="ml-10" />
      </template>
    </el-page-header>

    <template v-if="matter">
      <el-row :gutter="20" class="mt-20">
        <el-col :span="16">
          <!-- 基本信息 -->
          <el-card header="事项信息" shadow="never">
            <el-descriptions :column="3" border>
              <el-descriptions-item label="编号">{{ matter.matter_no }}</el-descriptions-item>
              <el-descriptions-item label="类型">{{ matter.type_name }}</el-descriptions-item>
              <el-descriptions-item label="负责人">{{ matter.owner_name }}</el-descriptions-item>
              <el-descriptions-item label="进度">
                <el-progress :percentage="matter.progress" :stroke-width="8" style="width: 150px" />
              </el-descriptions-item>
              <el-descriptions-item label="当前节点">{{ matter.current_node_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="截止日期">{{ formatDate(matter.due_date, 'YYYY-MM-DD') }}</el-descriptions-item>
              <el-descriptions-item label="成员" :span="3">
                <div class="member-list">
                  <el-tag v-for="m in matter.members" :key="m.user_id" size="small" :type="m.role_in_matter === 'owner' ? 'warning' : ''">
                    {{ m.user_name }}{{ m.role_in_matter === 'owner' ? ' (负责人)' : '' }}
                  </el-tag>
                  <el-button text type="primary" size="small" @click="showAddMember = true">
                    <el-icon><Plus /></el-icon>添加
                  </el-button>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="描述" :span="3">{{ matter.description || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- 流程节点 -->
          <el-card header="流程进度" shadow="never" class="mt-20" v-if="matter.nodes.length > 0">
            <div class="workflow-timeline">
              <div v-for="(node, index) in matter.nodes" :key="node.id" class="node-card" :class="'node-' + node.status">
                <div class="node-header">
                  <span class="node-order">{{ index + 1 }}</span>
                  <span class="node-name">{{ node.node_name }}</span>
                  <StatusTag :status="node.status" type="node" size="small" />
                </div>
                <div class="node-body">
                  <span>负责人: {{ node.owner_name }}</span>
                  <span v-if="node.planned_finish_time" class="ml-10">
                    <el-tag :type="getSlaTagType(node)" size="small" effect="plain">
                      {{ getSlaLabel(node) }}
                    </el-tag>
                  </span>
                  <div v-if="node.status === 'in_progress'" class="node-actions mt-10">
                    <el-button size="small" type="primary" @click="handleAdvance(node.id)">完成推进</el-button>
                    <el-button size="small" @click="handleRollback(node.id)">退回</el-button>
                    <el-button size="small" type="warning" @click="handleSkip(node.id)">跳过</el-button>
                  </div>
                </div>
              </div>
            </div>
          </el-card>

          <!-- 文档列表 -->
          <el-card header="相关文档" shadow="never" class="mt-20">
            <el-table :data="matter.documents" stripe>
              <el-table-column label="文件名" min-width="200">
                <template #default="{ row }">
                  <div class="file-info">
                    <FileTypeIcon :file-type="row.file_type" :size="20" />
                    <el-button text @click="$router.push(`/documents/${row.id}`)">{{ row.original_name }}</el-button>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="90">
                <template #default="{ row }"><StatusTag :status="row.status" type="document" /></template>
              </el-table-column>
              <el-table-column prop="owner_name" label="上传者" width="100" />
              <el-table-column prop="created_at" label="上传时间" width="160">
                <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>

        <el-col :span="8">
          <!-- 讨论区 -->
          <el-card header="讨论区" shadow="never">
            <div class="comment-list">
              <div v-for="c in matter.recent_comments" :key="c.id" class="comment-item">
                <div class="comment-user">{{ c.user_name }}</div>
                <div class="comment-content">{{ c.content }}</div>
                <div class="comment-time">{{ formatDate(c.created_at) }}</div>
              </div>
            </div>
            <div class="comment-input mt-10">
              <el-input v-model="newComment" placeholder="输入讨论内容..." type="textarea" :rows="2" />
              <el-button type="primary" size="small" class="mt-10" @click="handleComment" :loading="commenting">发送</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-dialog v-model="showAddMember" title="添加成员" width="400px">
      <el-select v-model="newMemberIds" placeholder="选择用户" multiple filterable style="width: 100%">
        <el-option v-for="u in userList" :key="u.id" :label="u.real_name" :value="u.id" />
      </el-select>
      <template #footer>
        <el-button @click="showAddMember = false">取消</el-button>
        <el-button type="primary" :loading="addingMember" @click="handleAddMember">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Plus } from '@element-plus/icons-vue'
import { useMatterStore } from '@/stores/matters'
import { usersApi } from '@/api/users'
import { workflowApi } from '@/api/workflow'
import { formatDate } from '@/utils/format'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { ElMessage } from 'element-plus'
import type { MatterDetail } from '@/api/matters'

const route = useRoute()
const matterStore = useMatterStore()

const loading = ref(true)
const matter = ref<MatterDetail | null>(null)
const newComment = ref('')
const commenting = ref(false)
const showAddMember = ref(false)
const newMemberIds = ref<number[]>([])
const userList = ref<any[]>([])
const addingMember = ref(false)

async function loadData() {
  loading.value = true
  try {
    matter.value = await matterStore.fetchMatter(Number(route.params.id))
  } finally {
    loading.value = false
  }
}

async function handleComment() {
  if (!newComment.value.trim()) return
  commenting.value = true
  try {
    await matterStore.addComment(Number(route.params.id), newComment.value.trim())
    newComment.value = ''
    await loadData()
  } finally {
    commenting.value = false
  }
}

async function handleAddMember() {
  addingMember.value = true
  try {
    await matterStore.addMembers(Number(route.params.id), newMemberIds.value)
    showAddMember.value = false
    newMemberIds.value = []
    ElMessage.success('成员添加成功')
  } finally {
    addingMember.value = false
  }
}

async function handleAdvance(nodeId: number) {
  try {
    await workflowApi.advanceNode(Number(route.params.id), nodeId)
    ElMessage.success('节点已推进')
    await loadData()
  } catch { /* handled */ }
}

async function handleRollback(nodeId: number) {
  try {
    await workflowApi.rollbackNode(Number(route.params.id), nodeId)
    ElMessage.success('节点已退回')
    await loadData()
  } catch { /* handled */ }
}

async function handleSkip(nodeId: number) {
  try {
    await workflowApi.skipNode(Number(route.params.id), nodeId)
    ElMessage.success('节点已跳过')
    await loadData()
  } catch { /* handled */ }
}

function getSlaTagType(node: any): string {
  if (node.sla_status === 'overdue') return 'danger'
  if (node.sla_status === 'at_risk') return 'warning'
  // Check if planned_finish_time is within 2 hours
  if (node.planned_finish_time) {
    const now = new Date().getTime()
    const planned = new Date(node.planned_finish_time).getTime()
    const hoursLeft = (planned - now) / (1000 * 60 * 60)
    if (hoursLeft < 0) return 'danger'
    if (hoursLeft < 2) return 'warning'
  }
  return 'success'
}

function getSlaLabel(node: any): string {
  if (node.sla_status === 'overdue') return 'SLA 已超时'
  if (node.sla_status === 'at_risk') return 'SLA 即将超时'
  if (node.planned_finish_time) {
    const now = new Date().getTime()
    const planned = new Date(node.planned_finish_time).getTime()
    const hoursLeft = (planned - now) / (1000 * 60 * 60)
    if (hoursLeft < 0) return 'SLA 已超时'
    if (hoursLeft < 2) return 'SLA 即将超时'
  }
  return 'SLA 正常'
}

onMounted(() => {
  loadData()
  usersApi.getList({ page_size: 200 }).then(r => userList.value = r.items)
})
</script>

<style scoped>
.mt-10 { margin-top: 10px; }
.mt-20 { margin-top: 20px; }
.ml-10 { margin-left: 10px; }
.page-title { font-size: 18px; font-weight: 600; }
.member-list { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.workflow-timeline { display: flex; flex-direction: column; gap: 12px; }
.node-card {
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
  background: #fafafa;
}
.node-card.node-completed { border-color: #67C23A; background: #f0f9eb; }
.node-card.node-in_progress { border-color: #409EFF; background: #ecf5ff; }
.node-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.node-order {
  width: 24px; height: 24px; border-radius: 50%;
  background: #409EFF; color: #fff; display: flex;
  align-items: center; justify-content: center; font-size: 12px;
}
.node-name { font-weight: 600; }
.node-body { padding-left: 34px; font-size: 13px; color: #666; }
.node-actions { display: flex; gap: 8px; }
.comment-list { max-height: 300px; overflow-y: auto; }
.comment-item { padding: 8px 0; border-bottom: 1px solid #f5f5f5; }
.comment-user { font-weight: 600; font-size: 13px; }
.comment-content { margin-top: 4px; font-size: 13px; }
.comment-time { font-size: 12px; color: #999; margin-top: 2px; }
.comment-input { border-top: 1px solid #f0f0f0; padding-top: 10px; }
.file-info { display: flex; align-items: center; gap: 8px; }
</style>

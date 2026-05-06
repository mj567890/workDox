<template>
  <div class="board-page">
    <div class="board-header">
      <el-button text @click="$router.push('/task-mgmt')">&larr; 返回任务列表</el-button>
      <h2 v-if="board">{{ board.title }}</h2>
      <div class="board-actions">
        <el-progress :percentage="board?.progress || 0" :stroke-width="16" :color="progressColor" style="width: 200px" />
        <el-button v-if="canAdvance" type="primary" @click="handleAdvance">推进到下一阶段</el-button>
      </div>
    </div>

    <div v-loading="loading">
      <div v-for="stage in board?.stages || []" :key="stage.id" class="stage-card">
        <div class="stage-header">
          <el-tag :type="stageStatusTag(stage.status)" size="large">
            {{ stage.name }}
          </el-tag>
          <span class="stage-status">{{ stage.status === 'locked' ? '🔒' : stage.status === 'in_progress' ? '▶️' : '✅' }}</span>
        </div>
        <div class="slot-grid">
          <div v-for="slot in stage.slots" :key="slot.id" class="slot-item" :class="slotClass(slot)">
            <div class="slot-icon">
              <span v-if="slot.status === 'filled'">📄</span>
              <span v-else-if="slot.status === 'waived'">🚫</span>
              <span v-else>⬜</span>
            </div>
            <div class="slot-info">
              <div class="slot-name">
                {{ slot.name }}
                <el-tag v-if="slot.is_required" size="small" type="danger">必填</el-tag>
              </div>
              <div class="slot-meta">
                <template v-if="slot.status === 'filled'">
                  <span class="maturity-tag">{{ maturityLabel(slot.maturity) }}</span>
                  <span v-if="slot.document_name">{{ slot.document_name }}</span>
                  <span v-if="slot.version_count">v{{ slot.version_count }}</span>
                </template>
                <template v-else-if="slot.status === 'waived'">
                  豁免: {{ slot.waive_reason }}
                </template>
                <template v-else>
                  待上传{{ slot.description ? ` — ${slot.description}` : '' }}
                </template>
              </div>
            </div>
            <div class="slot-actions" v-if="stage.status === 'in_progress'">
              <template v-if="slot.status === 'pending'">
                <el-button size="small" @click="openUpload(slot)">上传</el-button>
                <el-button size="small" @click="openWaive(slot)">豁免</el-button>
              </template>
              <template v-else-if="slot.status === 'filled'">
                <el-button size="small" @click="handleRemoveDoc(slot)">移除</el-button>
              </template>
              <template v-else-if="slot.status === 'waived'">
                <el-button size="small" @click="handleUnwaive(slot)">撤销豁免</el-button>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Upload dialog -->
    <el-dialog v-model="uploadDialog.visible" title="上传文档到槽位" width="400px">
      <el-form label-width="80px">
        <el-form-item label="文档 ID">
          <el-input-number v-model="uploadDialog.documentId" :min="1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="成熟度">
          <el-select v-model="uploadDialog.maturity" style="width: 100%">
            <el-option label="起草" value="draft" />
            <el-option label="修改" value="revision" />
            <el-option label="定稿" value="final" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="uploadDialog.maturity === 'custom'" label="说明">
          <el-input v-model="uploadDialog.maturityNote" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleUpload">确认</el-button>
      </template>
    </el-dialog>

    <!-- Waive dialog -->
    <el-dialog v-model="waiveDialog.visible" title="豁免槽位" width="400px">
      <el-input v-model="waiveDialog.reason" type="textarea" placeholder="请输入豁免理由" />
      <template #footer>
        <el-button @click="waiveDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleWaive">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { useTaskMgmtStore } from '@/stores/task-mgmt'
import { taskInstancesApi } from '@/api/task-instances'
import { ElMessage } from 'element-plus'

const route = useRoute()
const store = useTaskMgmtStore()
const loading = ref(false)
const actionLoading = ref('')
const board = computed(() => store.currentBoard)

const uploadDialog = reactive({ visible: false, slotId: 0, stageId: 0, documentId: 1, maturity: 'draft', maturityNote: '' })
const waiveDialog = reactive({ visible: false, slotId: 0, stageId: 0, reason: '' })

const taskId = computed(() => Number(route.params.id))

const canAdvance = computed(() => {
  if (!board.value) return false
  const cs = board.value.stages.find(s => s.status === 'in_progress')
  if (!cs) return false
  return cs.slots.filter(s => s.is_required && s.status === 'pending').length === 0
})

onMounted(async () => {
  loading.value = true
  try {
    await store.fetchBoard(taskId.value)
  } finally {
    loading.value = false
  }
})

function stageStatusTag(s: string) {
  const map: Record<string, string> = { locked: 'info', in_progress: 'warning', completed: 'success' }
  return map[s] || 'info'
}

function slotClass(slot: any) {
  if (slot.status === 'filled' && slot.maturity === 'final') return 'slot-final'
  if (slot.status === 'filled') return 'slot-filled'
  if (slot.status === 'waived') return 'slot-waived'
  if (slot.is_required) return 'slot-required'
  return ''
}

function maturityLabel(m: string | null) {
  const map: Record<string, string> = { draft: '起草', revision: '修改', final: '定稿', custom: '自定义' }
  return map[m || ''] || m || ''
}

function progressColor(pct: number) {
  if (pct >= 80) return '#67c23a'
  if (pct >= 40) return '#e6a23c'
  return '#f56c6c'
}

function openUpload(slot: any) {
  uploadDialog.slotId = slot.id
  uploadDialog.stageId = board.value?.stages.find(s => s.slots.some(sl => sl.id === slot.id))?.id || 0
  uploadDialog.documentId = 1
  uploadDialog.maturity = 'draft'
  uploadDialog.maturityNote = ''
  uploadDialog.visible = true
}

function openWaive(slot: any) {
  waiveDialog.slotId = slot.id
  waiveDialog.stageId = board.value?.stages.find(s => s.slots.some(sl => sl.id === slot.id))?.id || 0
  waiveDialog.reason = ''
  waiveDialog.visible = true
}

async function handleUpload() {
  actionLoading.value = 'upload'
  try {
    await taskInstancesApi.uploadToSlot(taskId.value, uploadDialog.stageId, uploadDialog.slotId, {
      document_id: uploadDialog.documentId,
      maturity: uploadDialog.maturity,
      maturity_note: uploadDialog.maturityNote || undefined,
    })
    uploadDialog.visible = false
    ElMessage.success('上传成功')
    await store.fetchBoard(taskId.value)
  } catch {
    // Error handled by API interceptor
  } finally {
    actionLoading.value = ''
  }
}

async function handleRemoveDoc(slot: any) {
  actionLoading.value = 'remove'
  try {
    const stageId = board.value?.stages.find(s => s.slots.some(sl => sl.id === slot.id))?.id || 0
    await taskInstancesApi.removeSlotDoc(taskId.value, stageId, slot.id)
    ElMessage.success('已移除')
    await store.fetchBoard(taskId.value)
  } catch {
    // Error handled by API interceptor
  } finally {
    actionLoading.value = ''
  }
}

async function handleWaive() {
  actionLoading.value = 'waive'
  try {
    await taskInstancesApi.waiveSlot(taskId.value, waiveDialog.stageId, waiveDialog.slotId, waiveDialog.reason)
    waiveDialog.visible = false
    ElMessage.success('已豁免')
    await store.fetchBoard(taskId.value)
  } catch {
    // Error handled by API interceptor
  } finally {
    actionLoading.value = ''
  }
}

async function handleUnwaive(slot: any) {
  actionLoading.value = 'unwaive'
  try {
    const stageId = board.value?.stages.find(s => s.slots.some(sl => sl.id === slot.id))?.id || 0
    await taskInstancesApi.unwaiveSlot(taskId.value, stageId, slot.id)
    ElMessage.success('已撤销豁免')
    await store.fetchBoard(taskId.value)
  } catch {
    // Error handled by API interceptor
  } finally {
    actionLoading.value = ''
  }
}

async function handleAdvance() {
  actionLoading.value = 'advance'
  try {
    await taskInstancesApi.advance(taskId.value)
    ElMessage.success('阶段已推进')
    await store.fetchBoard(taskId.value)
  } catch {
    // Error handled by API interceptor
  } finally {
    actionLoading.value = ''
  }
}
</script>

<style scoped>
.board-page { padding: 20px; }
.board-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.board-header h2 { margin: 0; flex: 1; }
.board-actions { display: flex; align-items: center; gap: 12px; }
.stage-card { margin-bottom: 16px; border: 1px solid #ebeef5; border-radius: 8px; padding: 16px; }
.stage-header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.stage-status { font-size: 18px; }
.slot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 8px; }
.slot-item { display: flex; align-items: center; gap: 8px; padding: 10px; border-radius: 6px; background: #fafafa; }
.slot-item.slot-final { background: #f0f9eb; }
.slot-item.slot-filled { background: #fdf6ec; }
.slot-item.slot-waived { background: #f2f3f5; }
.slot-item.slot-required { border-left: 3px solid #f56c6c; }
.slot-icon { font-size: 20px; width: 28px; text-align: center; }
.slot-info { flex: 1; min-width: 0; }
.slot-name { font-weight: 500; display: flex; align-items: center; gap: 4px; }
.slot-meta { font-size: 12px; color: #909399; margin-top: 2px; }
.maturity-tag { background: #ecf5ff; color: #409eff; padding: 1px 6px; border-radius: 3px; margin-right: 6px; }
.slot-actions { display: flex; gap: 4px; flex-shrink: 0; }
</style>

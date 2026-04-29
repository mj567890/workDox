<template>
  <el-card header="审批流程" shadow="never" class="approval-panel">
    <!-- Submit for review (owner only, when draft/rejected) -->
    <div v-if="canSubmit" class="submit-section">
      <el-alert
        :title="doc.status === 'rejected' ? '审批被驳回，可修改后重新提交' : '文档尚未提交审批'"
        :type="doc.status === 'rejected' ? 'warning' : 'info'"
        show-icon
        :closable="false"
        class="mb-16"
      />
      <div class="reviewer-select">
        <span class="label">选择审批人：</span>
        <el-select
          v-model="selectedReviewers"
          multiple
          filterable
          placeholder="请选择审批人（按顺序审批）"
          style="flex: 1"
        >
          <el-option
            v-for="u in users"
            :key="u.id"
            :label="u.real_name || u.username"
            :value="u.id"
            :disabled="u.id === authStore.user?.id"
          />
        </el-select>
      </div>
      <div class="review-chain mt-12" v-if="selectedReviewers.length > 0">
        <span class="label">审批顺序：</span>
        <div class="chain">
          <template v-for="(rid, idx) in selectedReviewers" :key="rid">
            <el-tag type="info" effect="plain" size="small">
              {{ idx + 1 }}. {{ getUserName(rid) }}
            </el-tag>
            <el-icon v-if="idx < selectedReviewers.length - 1" class="arrow"><ArrowRight /></el-icon>
          </template>
        </div>
      </div>
      <el-button
        type="primary"
        :loading="submitting"
        :disabled="selectedReviewers.length === 0"
        @click="handleSubmit"
        class="mt-16"
      >
        提交审批
      </el-button>
    </div>

    <!-- Review timeline -->
    <div v-if="reviews.length > 0" class="review-timeline">
      <div class="review-status-bar mb-16">
        <el-steps :active="activeStep" finish-status="success" process-status="process">
          <el-step
            v-for="r in reviews"
            :key="r.review_level"
            :title="`第${r.review_level}级`"
            :description="r.reviewer_name"
            :status="stepStatus(r.status)"
          />
        </el-steps>
      </div>

      <el-timeline>
        <el-timeline-item
          v-for="r in reviews"
          :key="r.id"
          :timestamp="r.reviewed_at || r.created_at"
          placement="top"
          :color="reviewColor(r.status)"
          :hollow="r.status === 'pending'"
        >
          <div class="review-item">
            <div class="review-header">
              <span class="review-level">第{{ r.review_level }}级审批</span>
              <span class="reviewer">- {{ r.reviewer_name }}</span>
              <el-tag :type="reviewTagType(r.status)" size="small" class="ml-8">
                {{ statusLabel(r.status) }}
              </el-tag>
            </div>
            <div v-if="r.comment" class="review-comment mt-4">
              <el-icon><ChatLineSquare /></el-icon>
              {{ r.comment }}
            </div>

            <!-- Review actions (for current reviewer) -->
            <div v-if="canReview(r)" class="review-actions mt-8">
              <el-input
                v-model="reviewComments[r.review_level]"
                type="textarea"
                :rows="2"
                placeholder="审批意见（可选）"
                class="mb-8"
              />
              <div class="action-buttons">
                <el-button type="success" size="small" :loading="approvingLevel === r.review_level" @click="handleApprove(r.review_level)">
                  批准
                </el-button>
                <el-button type="danger" size="small" :loading="rejectingLevel === r.review_level" @click="handleReject(r.review_level)">
                  驳回
                </el-button>
              </div>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </div>

    <!-- No reviews yet and not owner - pending state -->
    <div v-if="!canSubmit && reviews.length === 0 && doc.status !== 'approved'" class="empty-state">
      <el-empty description="暂无审批记录" :image-size="80" />
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ArrowRight, ChatLineSquare } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { documentsApi, type DocumentItem, type DocumentReview } from '@/api/documents'
import { usersApi } from '@/api/users'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  doc: DocumentItem
  reviews: DocumentReview[]
}>()

const emit = defineEmits<{
  refresh: []
}>()

const authStore = useAuthStore()

const users = ref<{ id: number; real_name: string; username: string }[]>([])
const selectedReviewers = ref<number[]>([])
const submitting = ref(false)
const approvingLevel = ref(0)
const rejectingLevel = ref(0)
const reviewComments = ref<Record<number, string>>({})

const canSubmit = computed(() => {
  return props.doc.owner_id === authStore.user?.id &&
    (props.doc.status === 'draft' || props.doc.status === 'rejected') &&
    props.reviews.length === 0
})

const activeStep = computed(() => {
  for (let i = 0; i < props.reviews.length; i++) {
    if (props.reviews[i].status === 'pending') return i
  }
  return props.reviews.length
})

function stepStatus(status: string) {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'error'
  return 'process'
}

function reviewColor(status: string) {
  if (status === 'approved') return '#67C23A'
  if (status === 'rejected') return '#F56C6C'
  return '#909399'
}

function reviewTagType(status: string) {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'info'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    pending: '待审批',
    approved: '已批准',
    rejected: '已驳回',
  }
  return map[status] || status
}

function canReview(review: DocumentReview) {
  return review.status === 'pending' &&
    review.reviewer_id === authStore.user?.id &&
    props.doc.status !== 'draft'
}

function getUserName(id: number) {
  const u = users.value.find(u => u.id === id)
  return u ? (u.real_name || u.username) : `用户#${id}`
}

async function loadUsers() {
  try {
    const res = await usersApi.getList({ page_size: 200 })
    users.value = res.items || []
  } catch {
    // ignore
  }
}

async function handleSubmit() {
  submitting.value = true
  try {
    await documentsApi.submitForReview(props.doc.id, selectedReviewers.value)
    ElMessage.success('已提交审批')
    selectedReviewers.value = []
    emit('refresh')
  } catch {
    // handled by interceptor
  } finally {
    submitting.value = false
  }
}

async function handleApprove(level: number) {
  approvingLevel.value = level
  try {
    await documentsApi.approve(props.doc.id, level, reviewComments.value[level] || undefined)
    ElMessage.success('已批准')
    emit('refresh')
  } catch {
    // handled
  } finally {
    approvingLevel.value = 0
  }
}

async function handleReject(level: number) {
  rejectingLevel.value = level
  try {
    await documentsApi.reject(props.doc.id, level, reviewComments.value[level] || undefined)
    ElMessage.warning('已驳回')
    emit('refresh')
  } catch {
    // handled
  } finally {
    rejectingLevel.value = 0
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.approval-panel {
  margin-bottom: 20px;
}
.mb-8 { margin-bottom: 8px; }
.mb-16 { margin-bottom: 16px; }
.mt-4 { margin-top: 4px; }
.mt-8 { margin-top: 8px; }
.mt-12 { margin-top: 12px; }
.mt-16 { margin-top: 16px; }
.ml-8 { margin-left: 8px; }
.reviewer-select {
  display: flex;
  align-items: center;
  gap: 12px;
}
.reviewer-select .label {
  white-space: nowrap;
  font-size: 14px;
  color: #606266;
}
.review-chain .label {
  font-size: 14px;
  color: #606266;
}
.chain {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.arrow {
  color: #c0c4cc;
}
.review-item {
  padding: 4px 0;
}
.review-header {
  display: flex;
  align-items: center;
  gap: 4px;
}
.review-level {
  font-weight: 500;
  font-size: 14px;
}
.reviewer {
  color: #909399;
  font-size: 13px;
}
.review-comment {
  color: #606266;
  font-size: 14px;
  background: #f5f7fa;
  padding: 8px 12px;
  border-radius: 4px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}
.review-actions {
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
}
.action-buttons {
  display: flex;
  gap: 8px;
}
.empty-state {
  padding: 20px 0;
}
.submit-section {
  margin-bottom: 8px;
}
</style>

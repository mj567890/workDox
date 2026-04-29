<template>
  <div class="document-detail" v-loading="loading">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="page-title">文档详情</span>
      </template>
    </el-page-header>

    <template v-if="doc">
      <el-alert v-if="lockStatus?.locked && lockStatus.locked_by !== authStore.user?.real_name"
        :title="`文档正在被 ${lockStatus.locked_by} 编辑中`" type="warning" show-icon :closable="false" class="mb-20" />

      <el-alert v-if="lockStatus?.locked && lockStatus.locked_by === authStore.user?.real_name"
        title="你正在编辑此文档。编辑完成后请上传新版本。" type="success" show-icon :closable="false" class="mb-20">
        <template #default>
          <el-button type="primary" size="small" @click="showVersionUpload = true">上传新版本</el-button>
          <el-button size="small" @click="handleUnlock">放弃编辑（解锁）</el-button>
        </template>
      </el-alert>

      <DocumentApprovalPanel
        :doc="doc"
        :reviews="reviews"
        @refresh="loadData"
      />

      <el-row :gutter="20">
        <el-col :span="16">
          <el-card header="文档信息" shadow="never">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="文件名">{{ doc.original_name }}</el-descriptions-item>
              <el-descriptions-item label="文件类型">
                <FileTypeIcon :file-type="doc.file_type" :size="20" />
                {{ doc.file_type.toUpperCase() }}
              </el-descriptions-item>
              <el-descriptions-item label="文件大小">{{ formatFileSize(doc.file_size) }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <StatusTag :status="doc.status" type="document" />
              </el-descriptions-item>
              <el-descriptions-item label="当前版本">v{{ doc.current_version_no || 1 }}</el-descriptions-item>
              <el-descriptions-item label="上传者">{{ doc.owner_name }}</el-descriptions-item>
              <el-descriptions-item label="所属事项">{{ doc.matter_title || '-' }}</el-descriptions-item>
              <el-descriptions-item label="文档分类">{{ doc.category_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="共享范围">{{ doc.permission_scope === 'matter' ? '事项内共享' : doc.permission_scope }}</el-descriptions-item>
              <el-descriptions-item label="标签">
                <el-tag v-for="tag in doc.tags" :key="tag.id" size="small" :color="tag.color" effect="light" class="mr-4">
                  {{ tag.name }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="描述" :span="2">{{ doc.description || '-' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card header="版本历史" shadow="never" class="mt-20">
            <div class="version-header">
              <el-button type="primary" size="small" @click="handleDownload">下载文档</el-button>
              <el-button v-if="canEdit && !lockStatus?.locked" size="small" @click="handleLockAndDownload">
                <el-icon><Lock /></el-icon>锁定并下载
              </el-button>
              <el-button v-if="canEdit" size="small" @click="showVersionUpload = true">上传新版本</el-button>
              <el-button v-if="canDeleteCurrentDoc" type="danger" size="small" @click="handleDeleteDocument">
                <el-icon><Delete /></el-icon>删除文档
              </el-button>
            </div>
            <el-timeline class="mt-20">
              <el-timeline-item
                v-for="v in versions"
                :key="v.id"
                :timestamp="formatDate(v.created_at)"
                placement="top"
                :color="v.is_official ? '#67C23A' : '#409EFF'"
              >
                <div class="version-item">
                  <div class="version-title">
                    <el-tag :type="v.is_official ? 'success' : 'info'" size="small">v{{ v.version_no }}</el-tag>
                    <el-tag v-if="v.is_official" type="success" size="small" effect="dark">正式版</el-tag>
                    <span class="version-user">{{ v.upload_user_name }}</span>
                  </div>
                  <div class="version-note" v-if="v.change_note">{{ v.change_note }}</div>
                  <div class="version-size">{{ formatFileSize(v.file_size) }}</div>
                  <div class="version-actions" v-if="canSetOfficial && !v.is_official">
                    <el-button text type="warning" size="small" @click="handleSetOfficial(v.id)">设为正式版</el-button>
                  </div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </el-card>
        </el-col>

        <el-col :span="8">
          <el-card header="预览" shadow="never">
            <div class="preview-area" v-if="previewStatus === 'ready'">
              <iframe :src="previewUrl" width="100%" height="400" frameborder="0" />
            </div>
            <div class="preview-area" v-else-if="previewStatus === 'processing'">
              <el-skeleton :rows="5" animated />
              <p class="text-center">文档转换中，请稍候...</p>
            </div>
            <div class="preview-area" v-else-if="previewStatus === 'unsupported'">
              <p class="text-center text-gray">此文件类型暂不支持预览</p>
              <el-button type="primary" @click="handleDownload" style="width:100%">下载查看</el-button>
            </div>
            <div class="preview-area" v-else>
              <el-button type="primary" @click="loadPreview" style="width:100%">加载预览</el-button>
            </div>
          </el-card>

          <el-card header="锁定状态" shadow="never" class="mt-20">
            <div v-if="lockStatus?.locked" class="lock-info">
              <p><el-icon><Lock /></el-icon> 锁定者: {{ lockStatus.locked_by }}</p>
              <p>锁定时间: {{ formatDate(lockStatus.locked_at) }}</p>
              <p>过期时间: {{ formatDate(lockStatus.expires_at) }}</p>
            </div>
            <div v-else>
              <p class="text-gray">文档未被锁定</p>
            </div>
          </el-card>

          <el-card header="智能处理" shadow="never" class="mt-20">
            <div v-if="!extractedText">
              <el-button type="primary" size="small" :loading="extracting" @click="handleExtractText">
                提取文档文本
              </el-button>
              <p class="text-gray mt-10" style="font-size: 12px">提取后可查看相似文档和智能建议</p>
            </div>
            <div v-else>
              <el-tag type="success" size="small" effect="light">已提取文本</el-tag>
              <span class="ml-8" style="font-size: 12px; color: #999">{{ extractedText.length }} 字符</span>
              <div style="margin-top: 12px; display: flex; gap: 8px">
                <el-button size="small" :loading="summarizing" @click="handleAISummarize">
                  AI 摘要
                </el-button>
                <el-button size="small" type="primary" @click="handleAIAsk">
                  AI 问答
                </el-button>
              </div>
            </div>
          </el-card>

          <el-dialog v-model="showSummary" title="AI 摘要" width="600px">
            <div style="line-height: 1.8; white-space: pre-wrap">{{ aiSummary }}</div>
          </el-dialog>
        </el-col>
      </el-row>

      <el-row :gutter="20" class="mt-20" v-if="extractedText">
        <el-col :span="24">
          <el-card header="相似文档" shadow="never">
            <div v-if="similarDocs.length === 0">
              <el-empty description="未找到相似文档" />
            </div>
            <el-table v-else :data="similarDocs" stripe size="small">
              <el-table-column prop="original_name" label="文档名称" min-width="200">
                <template #default="{ row }">
                  <el-link type="primary" @click="$router.push(`/documents/${row.document_id}`)">
                    {{ row.original_name }}
                  </el-link>
                </template>
              </el-table-column>
              <el-table-column prop="similarity_score" label="相似度" width="100">
                <template #default="{ row }">
                  <el-progress :percentage="Math.round(row.similarity_score * 100)" :stroke-width="8" />
                </template>
              </el-table-column>
              <el-table-column prop="headline" label="匹配摘要" min-width="250">
                <template #default="{ row }">
                  <span v-if="row.headline" v-html="row.headline" style="font-size: 12px; color: #666"></span>
                  <span v-else style="color: #ccc">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="90">
                <template #default="{ row }">
                  <StatusTag :status="row.status" type="document" />
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" class="mt-20">
        <el-col :span="24">
          <DocumentRelationGraph :doc-id="Number(route.params.id)" />
        </el-col>
      </el-row>
    </template>

    <el-dialog v-model="showVersionUpload" title="上传新版本" width="500px">
      <el-upload drag :auto-upload="false" :on-change="(f: any) => newVersionFile = f.raw" :limit="1">
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件或点击上传</div>
      </el-upload>
      <el-input v-model="changeNote" placeholder="变更说明" type="textarea" :rows="3" class="mt-20" />
      <el-checkbox v-model="setAsOfficial" class="mt-10">设为正式版</el-checkbox>
      <template #footer>
        <el-button @click="showVersionUpload = false">取消</el-button>
        <el-button type="primary" :loading="uploadingVersion" :disabled="!newVersionFile" @click="handleUploadVersion">
          确认上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Lock, UploadFilled, Delete } from '@element-plus/icons-vue'
import { useDocumentStore } from '@/stores/documents'
import { useAuthStore } from '@/stores/auth'
import { usePermission } from '@/composables/usePermission'
import { documentsApi, type DocumentItem, type DocumentVersion, type LockStatus, type DocumentReview } from '@/api/documents'
import { formatDate, formatFileSize } from '@/utils/format'
import { downloadFile } from '@/utils/download'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import DocumentApprovalPanel from './DocumentApprovalPanel.vue'
import DocumentRelationGraph from '@/components/documents/DocumentRelationGraph.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { aiApi } from '@/api/ai'

const route = useRoute()
const docStore = useDocumentStore()
const authStore = useAuthStore()
const { canEditDocument: canEdit, canSetOfficialVersion: canSetOfficial } = usePermission()

const canDeleteCurrentDoc = computed(() => {
  if (!doc.value || !authStore.user) return false
  return authStore.isAdmin || doc.value.owner_id === authStore.user.id
})

const loading = ref(true)
const doc = ref<DocumentItem | null>(null)
const versions = ref<DocumentVersion[]>([])
const reviews = ref<DocumentReview[]>([])
const lockStatus = ref<LockStatus | null>(null)
const previewStatus = ref('')
const previewUrl = ref('')
const showVersionUpload = ref(false)
const newVersionFile = ref<File | null>(null)
const changeNote = ref('')
const setAsOfficial = ref(false)
const uploadingVersion = ref(false)

// Document intelligence
const extracting = ref(false)
const similarDocs = ref<any[]>([])
const extractedText = ref<string | null>(null)

// AI features
const summarizing = ref(false)
const showSummary = ref(false)
const aiSummary = ref('')
const router = useRouter()

async function handleAISummarize() {
  summarizing.value = true
  try {
    const id = Number(route.params.id)
    const result = await aiApi.summarize(id)
    aiSummary.value = result.summary
    showSummary.value = true
  } catch {
    ElMessage.error('AI 摘要生成失败')
  } finally {
    summarizing.value = false
  }
}

function handleAIAsk() {
  router.push(`/ai/chat?document_id=${route.params.id}`)
}

async function loadData() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    doc.value = await documentsApi.getDetail(id)
    versions.value = await documentsApi.getVersions(id)
    reviews.value = await documentsApi.getReviews(id).catch(() => [] as DocumentReview[])
    lockStatus.value = await documentsApi.getLockStatus(id)

    // Check if text was already extracted
    if (doc.value?.extracted_text_length) {
      extractedText.value = 'extracted'
      loadSimilarDocs(id)
    }
  } finally {
    loading.value = false
  }
}

async function handleExtractText() {
  extracting.value = true
  try {
    const id = Number(route.params.id)
    const result = await documentsApi.extractText(id)
    if (result.extracted) {
      extractedText.value = 'extracted'
      ElMessage.success(`文本提取成功 (${result.length} 字符)`)
      loadSimilarDocs(id)
    } else {
      ElMessage.warning(result.detail || '无法提取文本')
    }
  } catch {
    ElMessage.error('文本提取失败')
  } finally {
    extracting.value = false
  }
}

async function loadSimilarDocs(docId: number) {
  try {
    similarDocs.value = await documentsApi.getSimilarDocuments(docId)
  } catch {
    similarDocs.value = []
  }
}

async function loadPreview() {
  const id = Number(route.params.id)
  try {
    const res = await documentsApi.getPreview(id)
    previewStatus.value = res.status
    if (res.url) previewUrl.value = res.url
  } catch {
    previewStatus.value = 'unsupported'
  }
}

function handleDownload() {
  const id = Number(route.params.id)
  const token = localStorage.getItem('token')
  const url = `/api/v1/documents/${id}/download?token=${token}`
  downloadFile(url, doc.value?.original_name || 'document')
}

async function handleLockAndDownload() {
  try {
    await documentsApi.lock(Number(route.params.id))
    await loadData()
    handleDownload()
    ElMessage.success('文档已锁定，请下载后编辑')
  } catch {
    // error handled by interceptor
  }
}

async function handleDeleteDocument() {
  try {
    await ElMessageBox.confirm(
      `确认删除文档「${doc.value?.original_name}」？删除后将无法恢复。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await documentsApi.delete(Number(route.params.id))
    ElMessage.success('文档已删除')
    router.push('/documents')
  } catch {
    // cancelled or error handled by interceptor
  }
}

async function handleUnlock() {
  try {
    await documentsApi.unlock(Number(route.params.id))
    lockStatus.value = null
    ElMessage.success('已解锁')
  } catch {
    // handled
  }
}

async function handleSetOfficial(versionId: number) {
  try {
    await ElMessageBox.confirm('确认将此版本设为正式版？', '确认操作')
    await documentsApi.setOfficialVersion(Number(route.params.id), versionId)
    await loadData()
    ElMessage.success('已设为正式版')
  } catch {
    // cancelled
  }
}

async function handleUploadVersion() {
  if (!newVersionFile.value) return
  uploadingVersion.value = true
  try {
    const formData = new FormData()
    formData.append('file', newVersionFile.value)
    formData.append('change_note', changeNote.value)
    formData.append('set_as_official', String(setAsOfficial.value))
    await documentsApi.uploadVersion(Number(route.params.id), formData)
    showVersionUpload.value = false
    newVersionFile.value = null
    changeNote.value = ''
    setAsOfficial.value = false
    await loadData()
    ElMessage.success('新版本已上传')
  } finally {
    uploadingVersion.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.document-detail {
  padding: 0;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
}
.mb-20 { margin-bottom: 20px; }
.mt-10 { margin-top: 10px; }
.mt-20 { margin-top: 20px; }
.mr-4 { margin-right: 4px; }
.text-center { text-align: center; }
.text-gray { color: #999; }
.version-header {
  display: flex;
  gap: 8px;
}
.version-item {
  padding: 4px 0;
}
.version-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.version-user {
  color: #666;
  font-size: 13px;
}
.version-note {
  color: #999;
  font-size: 13px;
  margin-bottom: 4px;
}
.version-size {
  color: #999;
  font-size: 12px;
}
.version-actions {
  margin-top: 8px;
}
.lock-info p {
  margin: 8px 0;
  display: flex;
  align-items: center;
  gap: 4px;
}
.ml-8 { margin-left: 8px; }
.preview-area {
  min-height: 200px;
}
</style>

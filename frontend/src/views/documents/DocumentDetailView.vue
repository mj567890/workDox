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
          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span>文档信息</span>
                <div v-if="canEdit">
                  <template v-if="!editMode">
                    <el-button type="primary" size="small" @click="startEdit">
                      <el-icon><Edit /></el-icon>编辑
                    </el-button>
                  </template>
                  <template v-else>
                    <el-button type="primary" size="small" :loading="savingEdit" @click="saveEdit">保存</el-button>
                    <el-button size="small" @click="cancelEdit">取消</el-button>
                  </template>
                </div>
              </div>
            </template>

            <!-- Read-only view -->
            <el-descriptions v-if="!editMode" :column="2" border>
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
              <el-descriptions-item label="文档分类">{{ doc.category_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="共享范围">{{ doc.permission_scope === 'private' ? '私有' : '全局可见' }}</el-descriptions-item>
              <el-descriptions-item label="标签">
                <el-tag v-for="tag in doc.tags" :key="tag.id" size="small" :color="tag.color" effect="light" class="mr-4">
                  {{ tag.name }}
                </el-tag>
                <span v-if="!doc.tags || doc.tags.length === 0" class="text-gray">-</span>
              </el-descriptions-item>
              <el-descriptions-item label="描述" :span="2">{{ doc.description || '-' }}</el-descriptions-item>
            </el-descriptions>

            <!-- Edit form -->
            <el-form v-else :model="editForm" label-width="80px" label-position="left">
              <el-form-item label="文件名">
                <el-input v-model="editForm.original_name" />
              </el-form-item>
              <el-form-item label="文档分类">
                <el-select v-model="editForm.category_id" placeholder="选择分类" clearable style="width:100%">
                  <el-option v-for="c in docStore.categories" :key="c.id" :label="c.name" :value="c.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="共享范围">
                <el-select v-model="editForm.permission_scope" style="width:100%">
                  <el-option label="私有" value="private" />
                  <el-option label="全局可见" value="global" />
                </el-select>
              </el-form-item>
              <el-form-item label="标签">
                <el-select v-model="editForm.tag_ids" multiple filterable placeholder="选择标签" style="width:100%">
                  <el-option v-for="t in docStore.tags" :key="t.id" :label="t.name" :value="t.id" />
                </el-select>
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="editForm.description" type="textarea" :rows="3" placeholder="文档描述" />
              </el-form-item>
            </el-form>
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
              <iframe v-if="previewFormat === 'html'" :srcdoc="previewContent" class="preview-iframe" sandbox="allow-same-origin" />
              <div v-else-if="previewFormat === 'markdown'" v-html="previewHtml" class="preview-content markdown-body"></div>
              <pre v-else class="preview-content preview-text">{{ previewContent }}</pre>
              <div v-if="previewFormat !== 'html' && canGenerateHtml" class="mt-10 text-center">
                <el-button size="small" type="warning" :loading="generatingPreview" @click="handleGeneratePreview">
                  生成 HTML 预览（保留排版）
                </el-button>
              </div>
            </div>
            <div class="preview-area" v-else-if="previewStatus === 'unsupported'">
              <p class="text-center text-gray">{{ previewDetail || '此文件类型暂不支持预览' }}</p>
              <el-button type="primary" @click="handleDownload" style="width:100%">下载查看</el-button>
            </div>
            <div class="preview-area" v-else-if="previewStatus === 'loading'">
              <el-skeleton :rows="8" animated />
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
import { Lock, UploadFilled, Delete, Edit } from '@element-plus/icons-vue'
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

// Edit mode
const editMode = ref(false)
const savingEdit = ref(false)
const editForm = ref({
  original_name: '',
  category_id: null as number | null,
  permission_scope: 'private',
  tag_ids: [] as number[],
  description: '',
})

function startEdit() {
  if (!doc.value) return
  editForm.value = {
    original_name: doc.value.original_name,
    category_id: doc.value.category_id,
    permission_scope: doc.value.permission_scope || 'private',
    tag_ids: (doc.value.tags || []).map(t => t.id),
    description: doc.value.description || '',
  }
  // Ensure categories & tags are loaded
  if (docStore.categories.length === 0) docStore.fetchCategories()
  if (docStore.tags.length === 0) docStore.fetchTags()
  editMode.value = true
}

function cancelEdit() {
  editMode.value = false
}

async function saveEdit() {
  savingEdit.value = true
  try {
    const id = Number(route.params.id)
    await documentsApi.update(id, {
      original_name: editForm.value.original_name,
      category_id: editForm.value.category_id,
      permission_scope: editForm.value.permission_scope,
      tag_ids: editForm.value.tag_ids,
      description: editForm.value.description,
    })
    editMode.value = false
    ElMessage.success('文档信息已更新')
    await loadData()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingEdit.value = false
  }
}

const loading = ref(true)
const doc = ref<DocumentItem | null>(null)
const versions = ref<DocumentVersion[]>([])
const reviews = ref<DocumentReview[]>([])
const lockStatus = ref<LockStatus | null>(null)
const previewStatus = ref('')
const previewContent = ref('')
const previewFormat = ref('text')
const previewHtml = ref('')
const previewDetail = ref('')
const canGenerateHtml = ref(false)

function renderMarkdown(text: string): string {
  // Minimal markdown renderer: headers, bold, italic, code, links, lists, tables
  let html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  // Tables — must run before other block-level transforms
  html = html.replace(/(?:^\|.+\|\s*$\n?)+/gm, (tableBlock) => {
    const lines = tableBlock.trim().split('\n').filter(l => l.includes('|'))
    if (lines.length < 2) return tableBlock
    // Skip separator line like |---|---|
    const dataLines = lines.filter(l => !/^\|[\s\-:]+\|[\s\-\|:]+$/.test(l))
    if (dataLines.length === 0) return tableBlock
    const header = dataLines[0]
    const cells = (line: string) => line.split('|').slice(1, -1).map(c => c.trim())
    const th = cells(header).map(c => `<th>${c}</th>`).join('')
    const thead = `<thead><tr>${th}</tr></thead>`
    const tbody = dataLines.length > 1
      ? `<tbody>${dataLines.slice(1).map(r => `<tr>${cells(r).map(c => `<td>${c}</td>`).join('')}</tr>`).join('')}</tbody>`
      : ''
    return `<table>${thead}${tbody}</table>`
  })

  // Headers
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>')
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  // Bold / italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  // Inline code
  html = html.replace(/`(.+?)`/g, '<code>$1</code>')
  // Links
  html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>')
  // Unordered lists
  html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
  // Line breaks
  html = html.replace(/^(?!<[hu]|<li|<t[a<h]|<t[b])(.+)$/gm, '<p>$1</p>')
  html = html.replace(/<p><\/p>/g, '')
  // Cleanup: merge adjacent <p> separated only by newlines
  html = html.replace(/\n\n/g, '<br/>')
  return html
}
const showVersionUpload = ref(false)
const newVersionFile = ref<File | null>(null)
const changeNote = ref('')
const setAsOfficial = ref(false)
const uploadingVersion = ref(false)

// Document intelligence
const extracting = ref(false)
const similarDocs = ref<any[]>([])
const extractedText = ref<string | null>(null)

// HTML preview generation
const generatingPreview = ref(false)

async function handleGeneratePreview() {
  generatingPreview.value = true
  try {
    const id = Number(route.params.id)
    await documentsApi.generatePreview(id)
    ElMessage.success('HTML 预览生成已启动，请等待 10-30 秒后刷新查看')
  } catch {
    ElMessage.error('启动预览生成失败')
  } finally {
    generatingPreview.value = false
  }
}

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
  previewStatus.value = 'loading'
  try {
    const res = await documentsApi.getPreviewText(id)
    if (res.has_content && res.content) {
      previewContent.value = res.content
      previewFormat.value = res.format
      canGenerateHtml.value = !!res.can_generate_html
      if (res.format === 'markdown') {
        previewHtml.value = renderMarkdown(res.content)
      }
      previewStatus.value = 'ready'
    } else {
      previewDetail.value = res.detail || '此文件类型暂不支持预览'
      canGenerateHtml.value = !!res.can_generate_html
      previewStatus.value = 'unsupported'
    }
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
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
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
.preview-content {
  max-height: 450px;
  overflow: auto;
}
.preview-iframe {
  width: 100%;
  height: 500px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
.preview-text {
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  line-height: 1.6;
  color: #303133;
  margin: 0;
  padding: 8px 0;
}
.markdown-body {
  font-size: 13px;
  line-height: 1.7;
  color: #303133;
}
.markdown-body h1 { font-size: 1.4em; border-bottom: 1px solid #eee; padding-bottom: 6px; margin: 12px 0 8px; }
.markdown-body h2 { font-size: 1.2em; margin: 10px 0 6px; }
.markdown-body h3 { font-size: 1.05em; margin: 8px 0 4px; }
.markdown-body h4 { font-size: 1em; margin: 6px 0 4px; }
.markdown-body p { margin: 4px 0; }
.markdown-body ul { padding-left: 20px; margin: 4px 0; }
.markdown-body li { margin: 2px 0; }
.markdown-body code { background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 0.9em; }
.markdown-body strong { font-weight: 600; }
.markdown-body a { color: #409EFF; }
</style>

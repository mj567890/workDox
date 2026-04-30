<template>
  <div class="drag-upload-zone">
    <div
      class="drop-zone"
      :class="{ 'is-dragover': isDragover }"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <el-icon class="drop-icon" :size="48"><UploadFilled /></el-icon>
      <p class="drop-text">拖拽文件到此处，或点击选择文件</p>
      <p class="drop-hint">支持 PDF、Word、Excel 等格式，单文件最大 500MB</p>
    </div>

    <div v-if="fileList.length > 0" class="file-list">
      <div v-for="file in fileList" :key="file.uid" class="file-item">
        <div class="file-meta">
          <el-icon class="file-icon"><Document /></el-icon>
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatSize(file.size) }}</span>
        </div>
        <el-progress
          class="file-progress"
          :percentage="file.progress"
          :status="file.status === 'error' ? 'exception' : file.status === 'done' ? 'success' : undefined"
          :stroke-width="12"
        />
        <div class="file-extra">
          <span v-if="file.status === 'uploading'" class="status-text uploading">
            <template v-if="file.speed">{{ file.speed }}</template>
            <template v-else>准备上传...</template>
          </span>
          <span v-if="file.status === 'error'" class="status-text error">上传失败</span>
          <span v-if="file.status === 'done'" class="status-text done">上传成功</span>
          <span v-if="file.size >= CHUNK_THRESHOLD && file.status === 'uploading'" class="large-file-hint">
            大文件上传中，请耐心等待...
          </span>
        </div>
      </div>
    </div>

    <input
      ref="fileInputRef"
      type="file"
      :multiple="multiple"
      :accept="accept"
      style="display: none"
      @change="handleFileSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import { UploadFilled, Document } from '@element-plus/icons-vue'
import { post } from '@/api/index'

const CHUNK_THRESHOLD = 100 * 1024 * 1024 // 100MB
const MAX_FILE_SIZE = 500 * 1024 * 1024   // 500MB

interface UploadFile {
  uid: string
  name: string
  size: number
  progress: number
  status: 'pending' | 'uploading' | 'done' | 'error'
  speed: string
  isLarge: boolean
}

const props = withDefaults(defineProps<{
  categoryId?: number | null
  multiple?: boolean
  accept?: string
}>(), {
  categoryId: null,
  multiple: true,
  accept: undefined,
})

const emit = defineEmits<{
  'upload-success': [fileName: string]
  'upload-error': [fileName: string]
}>()

const isDragover = ref(false)
const dragCounter = ref(0)
const fileList = ref<UploadFile[]>([])
const fileInputRef = ref<HTMLInputElement>()

function generateUid() {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
}

function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatSpeed(bytesPerSec: number): string {
  if (bytesPerSec < 1024) return bytesPerSec.toFixed(0) + ' B/s'
  if (bytesPerSec < 1024 * 1024) return (bytesPerSec / 1024).toFixed(1) + ' KB/s'
  return (bytesPerSec / (1024 * 1024)).toFixed(1) + ' MB/s'
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onDragOver(e: DragEvent) {
  e.dataTransfer!.dropEffect = 'copy'
  dragCounter.value++
  isDragover.value = true
}

function onDragLeave(e: DragEvent) {
  dragCounter.value--
  if (dragCounter.value <= 0) {
    dragCounter.value = 0
    isDragover.value = false
  }
}

function handleDrop(e: DragEvent) {
  dragCounter.value = 0
  isDragover.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) {
    processFiles(Array.from(files))
  }
}

function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const files = target.files
  if (files && files.length > 0) {
    processFiles(Array.from(files))
  }
  // Reset input value so the same file can be selected again
  target.value = ''
}

function processFiles(files: File[]) {
  const newFiles: UploadFile[] = []

  for (const rawFile of files) {
    if (rawFile.size > MAX_FILE_SIZE) {
      // File too large
      const largeFile: UploadFile = {
        uid: generateUid(),
        name: rawFile.name,
        size: rawFile.size,
        progress: 0,
        status: 'error',
        speed: '',
        isLarge: true,
      }
      newFiles.push(largeFile)
      emit('upload-error', rawFile.name)
      continue
    }

    const uploadFile: UploadFile = {
      uid: generateUid(),
      name: rawFile.name,
      size: rawFile.size,
      progress: 0,
      status: 'pending',
      speed: '',
      isLarge: rawFile.size >= CHUNK_THRESHOLD,
    }
    newFiles.push(uploadFile)
    fileList.value.push(uploadFile)

    // Start upload immediately
    uploadFileItem(uploadFile, rawFile)
  }
}

async function uploadFileItem(file: UploadFile, rawFile: File) {
  file.status = 'uploading'
  file.progress = 0
  file.speed = ''

  const formData = new FormData()
  formData.append('file', rawFile)
  if (props.categoryId) formData.append('category_id', String(props.categoryId))

  let lastLoaded = 0
  let lastTime = Date.now()

  try {
    await post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 600000, // 10 minutes for large files
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          file.progress = Math.round((progressEvent.loaded / progressEvent.total) * 100)

          const now = Date.now()
          const timeDiff = (now - lastTime) / 1000
          if (timeDiff >= 0.5) {
            const bytesPerSec = (progressEvent.loaded - lastLoaded) / timeDiff
            file.speed = formatSpeed(bytesPerSec)
            lastLoaded = progressEvent.loaded
            lastTime = now
          }
        }
      },
    })

    file.status = 'done'
    file.progress = 100
    emit('upload-success', rawFile.name)
  } catch {
    file.status = 'error'
    emit('upload-error', rawFile.name)
  }
}

onBeforeUnmount(() => {
  fileList.value = []
})
</script>

<style scoped>
.drag-upload-zone {
  width: 100%;
}

.drop-zone {
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.3s, background-color 0.3s;
  background-color: #fafafa;
}

.drop-zone:hover {
  border-color: #409eff;
  background-color: #f0f7ff;
}

.drop-zone.is-dragover {
  border-color: #409eff;
  background-color: #ecf5ff;
  box-shadow: 0 0 8px rgba(64, 158, 255, 0.3);
}

.drop-icon {
  color: #c0c4cc;
}

.drop-text {
  margin-top: 12px;
  font-size: 16px;
  color: #606266;
}

.drop-hint {
  margin-top: 8px;
  font-size: 13px;
  color: #c0c4cc;
}

.file-list {
  margin-top: 16px;
  max-height: 360px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  margin-bottom: 10px;
  background-color: #fff;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  color: #409eff;
  flex-shrink: 0;
}

.file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  color: #303133;
}

.file-size {
  flex-shrink: 0;
  font-size: 13px;
  color: #909399;
}

.file-progress {
  width: 100%;
}

.file-extra {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-text {
  font-size: 12px;
}

.status-text.uploading {
  color: #409eff;
}

.status-text.error {
  color: #f56c6c;
}

.status-text.done {
  color: #67c23a;
}

.large-file-hint {
  font-size: 12px;
  color: #e6a23c;
  font-style: italic;
}
</style>

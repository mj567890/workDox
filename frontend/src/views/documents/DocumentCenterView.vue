<template>
  <div class="document-center">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card header="文档分类" shadow="never">
          <el-menu class="category-menu">
            <el-menu-item index="all" @click="selectedCategory = null">
              <el-icon><Folder /></el-icon>全部文档
            </el-menu-item>
            <el-menu-item v-for="cat in docStore.categories" :key="cat.id" :index="String(cat.id)" @click="selectedCategory = cat.id">
              <el-icon><Folder /></el-icon>{{ cat.name }}
              <span class="cat-count">{{ cat.document_count }}</span>
            </el-menu-item>
          </el-menu>
        </el-card>

        <el-card header="标签" shadow="never" class="mt-20">
          <div class="tag-list">
            <el-tag
              v-for="tag in docStore.tags"
              :key="tag.id"
              :color="tag.color"
              :effect="selectedTag === tag.id ? 'dark' : 'plain'"
              class="tag-item"
              @click="selectedTag = selectedTag === tag.id ? null : tag.id"
              style="cursor: pointer"
            >
              {{ tag.name }}
            </el-tag>
          </div>
        </el-card>
      </el-col>

      <el-col :span="18">
        <el-card shadow="never">
          <div class="toolbar">
            <div class="toolbar-left">
              <el-input v-model="keyword" placeholder="搜索文档名称" clearable style="width: 250px" @input="handleSearch" />
              <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 130px" @change="fetchData">
                <el-option label="草稿" value="draft" />
                <el-option label="已提交" value="submitted" />
                <el-option label="审批中" value="reviewing" />
                <el-option label="已批准" value="approved" />
                <el-option label="已驳回" value="rejected" />
                <el-option label="正式版" value="official" />
              </el-select>
              <el-select v-model="filterFileType" placeholder="文件类型" clearable style="width: 120px" @change="fetchData">
                <el-option label="Word" value="docx" />
                <el-option label="Excel" value="xlsx" />
                <el-option label="PDF" value="pdf" />
                <el-option label="图片" value="jpg" />
                <el-option label="文本" value="txt" />
              </el-select>
            </div>
            <div class="toolbar-right">
              <el-dropdown @command="handleExport">
                <el-button type="default">
                  导出 <el-icon><ArrowDown /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="excel">导出 Excel</el-dropdown-item>
                    <el-dropdown-item command="pdf" disabled>导出 PDF</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button type="primary" @click="showUploader = true">
                <el-icon><Upload /></el-icon>上传文档
              </el-button>
            </div>
          </div>

          <div v-if="loading">
            <el-skeleton :rows="8" animated />
          </div>
          <div v-else>
            <el-table :data="docStore.documents" stripe @row-click="(row: any) => $router.push(`/documents/${row.id}`)" style="cursor: pointer">
            <el-table-column label="文件名" min-width="250">
              <template #default="{ row }">
                <div class="file-info">
                  <FileTypeIcon :file-type="row.file_type" :size="28" />
                  <span class="file-name">{{ row.original_name }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }"><StatusTag :status="row.status" type="document" /></template>
            </el-table-column>
            <el-table-column label="版本" width="70">
              <template #default="{ row }">v{{ row.current_version_no || 1 }}</template>
            </el-table-column>
            <el-table-column prop="file_size" label="大小" width="100">
              <template #default="{ row }">{{ formatFileSize(row.file_size) }}</template>
            </el-table-column>
            <el-table-column prop="owner_name" label="上传者" width="100" />
            <el-table-column prop="matter_title" label="所属事项" width="150" />
            <el-table-column label="标签" width="160">
              <template #default="{ row }">
                <el-tag v-for="tag in row.tags" :key="tag.id" size="small" :color="tag.color" effect="light" class="mr-4">
                  {{ tag.name }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" width="160">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button text type="primary" size="small" @click.stop="$router.push(`/documents/${row.id}`)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="docStore.total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              @change="fetchData"
            />
          </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 上传对话框 - 集成拖拽上传组件 -->
    <el-dialog v-model="showUploader" title="上传文档" width="650px" @close="resetUpload">
      <el-form class="mb-20" label-width="80px">
        <el-form-item label="所属事项">
          <el-select v-model="uploadMatterId" placeholder="选择事项（可选）" clearable filterable>
            <el-option v-for="m in uploadMatterList" :key="m.id" :label="m.title" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="文档分类">
          <el-select v-model="uploadCategoryId" placeholder="选择分类（可选）" clearable>
            <el-option v-for="c in docStore.categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
      </el-form>

      <DragUploadZone
        :matter-id="uploadMatterId"
        :category-id="uploadCategoryId"
        accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif"
        @upload-success="onUploadSuccess"
        @upload-error="onUploadError"
      />

      <template #footer>
        <el-button @click="showUploader = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Upload, Folder, ArrowDown } from '@element-plus/icons-vue'
import { useDocumentStore } from '@/stores/documents'
import { mattersApi } from '@/api/matters'
import { formatFileSize, formatDate } from '@/utils/format'
import { usePagination } from '@/composables/usePagination'
import FileTypeIcon from '@/components/common/FileTypeIcon.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import DragUploadZone from '@/components/common/DragUploadZone.vue'
import { ElMessage } from 'element-plus'

const docStore = useDocumentStore()
const { page, pageSize, setPage, setPageSize, setTotal } = usePagination()
const loading = ref(true)

const keyword = ref('')
const filterStatus = ref('')
const filterFileType = ref('')
const selectedCategory = ref<number | null>(null)
const selectedTag = ref<number | null>(null)
const showUploader = ref(false)
const uploadMatterId = ref<number | null>(null)
const uploadCategoryId = ref<number | null>(null)
const uploadMatterList = ref<any[]>([])

let searchTimer: ReturnType<typeof setTimeout>

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchData, 300)
}

async function fetchData() {
  await docStore.fetchDocuments({
    page: page.value,
    page_size: pageSize.value,
    keyword: keyword.value || undefined,
    status: filterStatus.value || undefined,
    file_type: filterFileType.value || undefined,
    category_id: selectedCategory.value || undefined,
    tag_id: selectedTag.value || undefined,
  })
  setTotal(docStore.total)
}

function onUploadSuccess(fileName: string) {
  ElMessage.success(`文件 "${fileName}" 上传成功`)
  fetchData()
}

function onUploadError(fileName: string) {
  ElMessage.error(`文件 "${fileName}" 上传失败`)
}

async function handleExport(command: string) {
  if (command === 'excel') {
    const token = localStorage.getItem('token')
    const response = await fetch('/api/v1/documents/export/excel', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `documents_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
  }
}

function resetUpload() {
  uploadMatterId.value = null
  uploadCategoryId.value = null
}

onMounted(async () => {
  loading.value = true
  await Promise.all([
    docStore.fetchCategories(),
    docStore.fetchTags(),
    fetchData(),
  ])
  loading.value = false
  mattersApi.getList({ page_size: 100 }).then(res => {
    uploadMatterList.value = res.items
  }).catch(() => {
    // matters API not available, dropdown will be empty
  })
})
</script>

<style scoped>
.mt-20 { margin-top: 20px; }
.mr-4 { margin-right: 4px; }
.mb-20 { margin-bottom: 20px; }
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}
.toolbar-left {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}
.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.category-menu {
  border-right: none;
}
.category-menu .el-menu-item {
  height: 40px;
  line-height: 40px;
}
.cat-count {
  margin-left: auto;
  color: #999;
  font-size: 12px;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.tag-item {
  cursor: pointer;
}
</style>

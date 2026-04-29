<template>
  <div class="search-results">
    <h2>搜索结果</h2>

    <el-card shadow="never">
      <div class="search-bar">
        <el-input v-model="keyword" placeholder="搜索文档、事项..." size="large" @keyup.enter="handleSearch">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" size="large" @click="handleSearch">搜索</el-button>
      </div>

      <div class="search-filters mt-20">
        <el-radio-group v-model="searchScope" @change="handleSearch">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="documents">文档</el-radio-button>
          <el-radio-button value="matters">事项</el-radio-button>
        </el-radio-group>
        <el-select v-model="filterFileType" placeholder="文件类型" clearable @change="handleSearch" v-if="searchScope !== 'matters'">
          <el-option label="Word" value="docx" />
          <el-option label="Excel" value="xlsx" />
          <el-option label="PDF" value="pdf" />
        </el-select>
      </div>

      <div v-loading="loading" class="results-area mt-20">
        <div v-if="results.length > 0">
          <div v-for="item in results" :key="`${item.type}-${item.id}`" class="result-item" @click="navigateTo(item)">
            <div class="result-title">
              <el-tag size="small" :type="item.type === 'document' ? '' : 'success'">{{ item.type === 'document' ? '文档' : '事项' }}</el-tag>
              <span class="result-name" v-html="item.highlight || item.title"></span>
            </div>
            <div class="result-desc" v-if="item.description">{{ item.description }}</div>
          </div>
        </div>
        <el-empty v-else-if="!loading && searched" description="未找到相关结果" />

        <div class="pagination-wrap" v-if="total > 0">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @change="handleSearch"
          />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { searchApi } from '@/api/search'

const route = useRoute()
const router = useRouter()

const keyword = ref('')
const searchScope = ref('all')
const filterFileType = ref('')
const loading = ref(false)
const searched = ref(false)
const results = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

async function handleSearch() {
  if (!keyword.value.trim()) return
  loading.value = true
  searched.value = true
  try {
    const res = await searchApi.search({
      keyword: keyword.value.trim(),
      scope: searchScope.value,
      file_type: filterFileType.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    results.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function navigateTo(item: any) {
  if (item.type === 'document') {
    router.push(`/documents/${item.id}`)
  } else if (item.type === 'matter') {
    router.push(`/matters/${item.id}`)
  }
}

onMounted(() => {
  const q = route.query.q as string
  if (q) {
    keyword.value = q
    handleSearch()
  }
})
</script>

<style scoped>
.search-results h2 { margin: 0 0 20px; }
.mt-20 { margin-top: 20px; }
.search-bar { display: flex; gap: 12px; }
.search-bar .el-input { flex: 1; }
.search-filters { display: flex; gap: 12px; align-items: center; }
.results-area { min-height: 300px; }
.result-item {
  padding: 12px;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
}
.result-item:hover { background: #f5f5f5; }
.result-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.result-name { font-size: 15px; font-weight: 500; }
.result-desc {
  margin-top: 6px;
  font-size: 13px;
  color: #666;
  padding-left: 52px;
}
.pagination-wrap { margin-top: 20px; display: flex; justify-content: flex-end; }
</style>

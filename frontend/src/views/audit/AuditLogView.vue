<template>
  <div class="audit-log">
    <h2>操作日志</h2>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="keyword" placeholder="搜索操作详情" clearable style="width: 200px" @input="handleSearch" />
        <el-select v-model="filterType" placeholder="操作类型" clearable @change="fetchData">
          <el-option label="登录" value="login" />
          <el-option label="上传" value="upload" />
          <el-option label="下载" value="download" />
          <el-option label="删除" value="delete" />
          <el-option label="锁定" value="lock" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="fetchData"
        />
      </div>

      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="user_name" label="操作人" width="100" />
        <el-table-column prop="operation_type" label="操作类型" width="120" />
        <el-table-column prop="target_type" label="目标类型" width="100" />
        <el-table-column prop="target_id" label="目标ID" width="80" />
        <el-table-column prop="detail" label="详情" min-width="200" />
        <el-table-column prop="ip_address" label="IP地址" width="140" />
        <el-table-column prop="created_at" label="操作时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @change="fetchData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { auditApi, type AuditLogItem } from '@/api/audit'
import { usePagination } from '@/composables/usePagination'
import { formatDate } from '@/utils/format'

const { page, pageSize, setTotal } = usePagination()
const loading = ref(false)
const logs = ref<AuditLogItem[]>([])
const total = ref(0)
const keyword = ref('')
const filterType = ref('')
const dateRange = ref<[Date, Date] | null>(null)

let searchTimer: ReturnType<typeof setTimeout>

function handleSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchData, 300)
}

async function fetchData() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: page.value,
      page_size: pageSize.value,
      operation_type: filterType.value || undefined,
    }
    if (dateRange.value) {
      params.start_date = dateRange.value[0].toISOString()
      params.end_date = dateRange.value[1].toISOString()
    }
    const res = await auditApi.getList(params)
    logs.value = res.items
    total.value = res.total
    setTotal(res.total)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<style scoped>
.audit-log h2 { margin: 0 0 20px; }
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>

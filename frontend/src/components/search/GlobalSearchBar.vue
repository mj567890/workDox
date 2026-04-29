<template>
  <div class="global-search">
    <el-input
      v-model="keyword"
      placeholder="搜索文档、事项..."
      :prefix-icon="Search"
      size="default"
      class="search-input"
      @keyup.enter="handleSearch"
      clearable
    >
      <template #append>
        <el-button :icon="Search" @click="handleSearch" />
      </template>
    </el-input>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const keyword = ref('')

function handleSearch() {
  if (keyword.value.trim()) {
    router.push({ path: '/search', query: { q: keyword.value.trim() } })
  }
}
</script>

<style scoped>
.global-search {
  max-width: 400px;
  width: 100%;
}
.search-input {
  width: 100%;
}
</style>

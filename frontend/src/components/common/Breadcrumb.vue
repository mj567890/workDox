<template>
  <el-breadcrumb separator="/" class="app-breadcrumb">
    <template v-for="(item, index) in breadcrumbs" :key="item.path">
      <el-breadcrumb-item :to="item.clickable ? item.path : undefined">
        {{ item.title }}
      </el-breadcrumb-item>
    </template>
  </el-breadcrumb>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const props = defineProps<{
  itemName?: string
}>()

const route = useRoute()

const breadcrumbs = computed(() => {
  const items = route.matched
    .filter((r) => r.meta?.title || r.name)
    .map((r, index, arr) => {
      const isLast = index === arr.length - 1
      let title: string

      if (r.path === '') {
        title = '工作台'
      } else if (isLast && props.itemName) {
        title = props.itemName
      } else {
        title = (r.meta?.title as string) || (r.name as string)
      }

      // 对于动态路由且没有 itemName 的情况，使用路由 name 或显示默认文本
      if (isLast && !props.itemName && /\:\w+/.test(r.path)) {
        const defaultName = r.name ? String(r.name) : '详情'
        title = String(r.meta?.title || defaultName)
      }

      return {
        title,
        path: r.path,
        clickable: !isLast,
      }
    })

  return items
})
</script>

<style scoped>
.app-breadcrumb {
  padding: 12px 0;
  font-size: 14px;
}

.app-breadcrumb :deep(.el-breadcrumb__item) {
  font-size: 14px;
}

.app-breadcrumb :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: #606266;
  cursor: default;
}

.app-breadcrumb :deep(.el-breadcrumb__inner) {
  color: #409eff;
  font-weight: normal;
  transition: color 0.2s;
}

.app-breadcrumb :deep(.el-breadcrumb__inner.is-link:hover) {
  color: #66b1ff;
}
</style>

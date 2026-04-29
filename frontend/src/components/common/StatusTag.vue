<template>
  <el-tag :type="config.color as any" :size="size" :effect="effect">
    {{ config.label }}
  </el-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  DOCUMENT_STATUS,
  MATTER_STATUS,
  TASK_PRIORITY,
  TASK_STATUS,
  NODE_STATUS,
} from '@/utils/constants'

const props = withDefaults(defineProps<{
  status: string
  type?: 'document' | 'matter' | 'task' | 'task_priority' | 'node'
  size?: '' | 'small' | 'default'
  effect?: '' | 'dark' | 'light' | 'plain'
}>(), {
  type: 'document',
  effect: 'light',
})

const statusMap: Record<string, Record<string, { label: string; color: string }>> = {
  document: DOCUMENT_STATUS,
  matter: MATTER_STATUS,
  task: TASK_STATUS,
  task_priority: TASK_PRIORITY,
  node: NODE_STATUS,
}

const config = computed(() => {
  const map = statusMap[props.type] || DOCUMENT_STATUS
  return map[props.status] || { label: props.status, color: 'info' }
})
</script>

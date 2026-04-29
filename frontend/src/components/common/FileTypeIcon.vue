<template>
  <el-icon :size="size" :color="color">
    <component :is="iconName" />
  </el-icon>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Document, Grid, Picture, FolderOpened, Edit, VideoCamera } from '@element-plus/icons-vue'
import { FILE_TYPE_ICONS } from '@/utils/constants'

const props = withDefaults(defineProps<{
  fileType: string
  size?: number
  color?: string
}>(), {
  size: 24,
})

const iconName = computed(() => FILE_TYPE_ICONS[props.fileType] || 'Document')
</script>

<template>
  <el-avatar :size="size" :src="avatarUrl">
    <el-icon :size="Math.floor(size / 2)"><UserFilled /></el-icon>
  </el-avatar>
</template>

<script setup lang="ts">
import { UserFilled } from '@element-plus/icons-vue'

withDefaults(defineProps<{
  avatarUrl?: string | null
  size?: number
}>(), {
  size: 32,
})
</script>

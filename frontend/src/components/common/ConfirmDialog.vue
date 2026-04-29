<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <slot />
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button :type="confirmType" :loading="loading" @click="handleConfirm">
        {{ confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(defineProps<{
  title?: string
  confirmText?: string
  confirmType?: 'primary' | 'danger' | 'warning'
  width?: string
}>(), {
  title: '确认操作',
  confirmText: '确认',
  confirmType: 'primary',
  width: '500px',
})

const emit = defineEmits<{ confirm: []; close: [] }>()

const visible = ref(false)
const loading = ref(false)

function show() {
  visible.value = true
}

function handleClose() {
  visible.value = false
  emit('close')
}

async function handleConfirm() {
  loading.value = true
  try {
    emit('confirm')
  } finally {
    loading.value = false
  }
}

defineExpose({ show })
</script>

<template>
  <router-view />
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationStore } from '@/stores/notifications'

const authStore = useAuthStore()
const notificationStore = useNotificationStore()

onMounted(() => {
  const token = localStorage.getItem('token')
  if (token && !authStore.user) {
    authStore.fetchUser().then(() => {
      notificationStore.initWebSocket()
    })
  } else if (token && authStore.user) {
    notificationStore.initWebSocket()
  }
})
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}

html.dark {
  color-scheme: dark;
}
</style>

<template>
  <el-popover placement="bottom-end" :width="360" trigger="click" @show="fetchNotifications">
    <template #reference>
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
        <el-button text :icon="Bell" />
      </el-badge>
    </template>
    <div class="notification-popover">
      <div class="notification-header">
        <span>通知</span>
        <el-button text type="primary" size="small" @click="markAll">全部已读</el-button>
      </div>
      <div class="notification-list" v-loading="loading">
        <div
          v-for="item in notificationStore.notifications"
          :key="item.id"
          class="notification-item"
          :class="{ unread: !item.is_read }"
          @click="handleClick(item)"
        >
          <div class="notification-title">{{ item.title }}</div>
          <div class="notification-time">{{ formatDate(item.created_at) }}</div>
        </div>
        <el-empty v-if="notificationStore.notifications.length === 0 && !loading" description="暂无通知" />
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Bell } from '@element-plus/icons-vue'
import { useNotificationStore } from '@/stores/notifications'
import { formatDate } from '@/utils/format'
import { useRouter } from 'vue-router'

const router = useRouter()
const notificationStore = useNotificationStore()
const loading = ref(false)

const unreadCount = ref(0)

async function fetchNotifications() {
  loading.value = true
  try {
    await notificationStore.fetchNotifications({ page_size: 10 })
    await notificationStore.fetchUnreadCount()
    unreadCount.value = notificationStore.unreadCount
  } finally {
    loading.value = false
  }
}

async function markAll() {
  await notificationStore.markAllAsRead()
  unreadCount.value = 0
}

function handleClick(item: any) {
  if (!item.is_read) {
    notificationStore.markAsRead(item.id)
  }
}

onMounted(() => {
  notificationStore.fetchUnreadCount().then(() => {
    unreadCount.value = notificationStore.unreadCount
  })
})
</script>

<style scoped>
.notification-popover {
  max-height: 400px;
}
.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 8px;
  font-weight: 600;
}
.notification-list {
  max-height: 320px;
  overflow-y: auto;
}
.notification-item {
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
}
.notification-item:hover {
  background: #f5f5f5;
}
.notification-item.unread {
  background: #e6f7ff;
}
.notification-title {
  font-size: 13px;
  line-height: 1.4;
}
.notification-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style>

<template>
  <div class="header-bar">
    <div class="header-left">
      <el-button v-if="showMenuButton" text @click="$emit('openMenu')" class="menu-btn">
        <el-icon :size="20"><Menu /></el-icon>
      </el-button>
      <el-button v-else text @click="$emit('toggleCollapse')">
        <el-icon :size="20"><Fold v-if="!isCollapsed" /><Expand v-else /></el-icon>
      </el-button>
      <GlobalSearchBar class="search-bar" />
    </div>
    <div class="header-right">
      <el-button text class="dashboard-link" @click="openDashboard">
        <el-icon :size="18"><DataAnalysis /></el-icon>
        <span class="dashboard-text">数据展板</span>
      </el-button>
      <NotificationBell />
      <el-button circle :icon="isDark ? Sunny : Moon" @click="toggleTheme" />
      <el-dropdown trigger="click" @command="handleCommand">
        <span class="user-info">
          <el-avatar :size="32" :icon="UserFilled" />
          <span class="user-name">{{ user?.real_name || user?.username }}</span>
          <el-icon><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">个人信息</el-dropdown-item>
            <el-dropdown-item command="password">修改密码</el-dropdown-item>
            <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Fold, Expand, Menu, ArrowDown, UserFilled, Sunny, Moon, DataAnalysis } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import GlobalSearchBar from '@/components/search/GlobalSearchBar.vue'
import NotificationBell from '@/components/notifications/NotificationBell.vue'
import { useTheme } from '@/composables/useTheme'

defineProps<{ isCollapsed?: boolean; showMenuButton?: boolean }>()
defineEmits<{ toggleCollapse: []; openMenu: [] }>()

const router = useRouter()
const authStore = useAuthStore()
const user = computed(() => authStore.user)
const { isDark, toggleTheme } = useTheme()

function openDashboard() {
  window.open('/dashboard', '_blank')
}

function handleCommand(command: string) {
  if (command === 'logout') {
    authStore.logout()
  } else if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'password') {
    router.push('/settings')
  }
}
</script>

<style scoped>
.header-bar {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}
.user-info:hover {
  background: #f5f5f5;
}
.user-name {
  font-size: 14px;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dashboard-link {
  font-size: 14px;
  color: #606266;
}
.dashboard-text {
  margin-left: 4px;
}

@media (max-width: 767px) {
  .search-bar {
    display: none;
  }
  .user-name {
    display: none;
  }
  .header-right {
    gap: 8px;
  }
  .dashboard-text {
    display: none;
  }
}
</style>

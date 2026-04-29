<template>
  <el-container class="app-layout">
    <!-- Desktop sidebar -->
    <el-aside
      v-if="!isMobile"
      :width="isCollapsed ? '64px' : '220px'"
      class="app-sidebar"
    >
      <Sidebar :is-collapsed="isCollapsed" />
    </el-aside>

    <!-- Mobile drawer -->
    <el-drawer
      v-model="mobileDrawerVisible"
      direction="ltr"
      size="260px"
      :with-header="false"
      :close-on-click-modal="true"
      class="mobile-drawer"
    >
      <Sidebar :is-collapsed="false" @navigate="mobileDrawerVisible = false" />
    </el-drawer>

    <el-container>
      <el-header class="app-header" height="56px">
        <HeaderBar
          :show-menu-button="isMobile"
          @toggle-collapse="isCollapsed = !isCollapsed"
          @open-menu="mobileDrawerVisible = true"
        />
      </el-header>
      <el-main class="app-main" :class="{ 'mobile-main': isMobile }">
        <Breadcrumb v-if="!isMobile" />
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <!-- Keyboard Shortcuts Help Dialog -->
  <el-dialog
    v-model="shortcutsHelpVisible"
    title="键盘快捷键"
    :width="isMobile ? '95%' : '480px'"
    :fullscreen="isMobile"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <el-table :data="shortcutsList" stripe size="small">
      <el-table-column prop="key" label="快捷键" width="140" />
      <el-table-column prop="description" label="功能" />
    </el-table>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import Sidebar from './Sidebar.vue'
import HeaderBar from './HeaderBar.vue'
import Breadcrumb from '../common/Breadcrumb.vue'
import { useShortcuts } from '@/composables/useShortcuts'
import { useResponsive } from '@/composables/useResponsive'

const { isMobile, isDesktop } = useResponsive()

const isCollapsed = ref(false)
const mobileDrawerVisible = ref(false)
const shortcutsHelpVisible = ref(false)

const shortcutsList = [
  { key: 'Ctrl + K', description: '全局搜索' },
  { key: 'Ctrl + N', description: '新建事项' },
  { key: 'Ctrl + B', description: '折叠侧栏' },
  { key: 'Esc', description: '关闭弹窗' },
  { key: '?', description: '显示此帮助' },
]

useShortcuts()

function handleToggleSidebar() {
  if (isMobile.value) {
    mobileDrawerVisible.value = !mobileDrawerVisible.value
  } else {
    isCollapsed.value = !isCollapsed.value
  }
}

function handleShowShortcutsHelp() {
  shortcutsHelpVisible.value = true
}

onMounted(() => {
  window.addEventListener('toggle-sidebar', handleToggleSidebar)
  window.addEventListener('show-shortcuts-help', handleShowShortcutsHelp)
})

onUnmounted(() => {
  window.removeEventListener('toggle-sidebar', handleToggleSidebar)
  window.removeEventListener('show-shortcuts-help', handleShowShortcutsHelp)
})
</script>

<style scoped>
.app-layout {
  height: 100vh;
}
.app-sidebar {
  background-color: #001529;
  transition: width 0.3s;
  overflow: hidden;
}
.app-header {
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  align-items: center;
  padding: 0 16px;
}
.app-main {
  background: #f0f2f5;
  min-height: calc(100vh - 56px);
  padding: 20px;
}
.mobile-main {
  padding: 12px 8px;
}
</style>

<style>
/* Mobile drawer override */
.mobile-drawer .el-drawer__body {
  padding: 0;
  background-color: #001529;
}
</style>

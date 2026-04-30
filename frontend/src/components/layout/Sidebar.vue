<template>
  <div class="sidebar">
    <div class="logo">
      <img src="@/assets/logo.svg" alt="logo" v-if="!isCollapsed" class="logo-img" />
      <span v-if="!isCollapsed" class="logo-text">WorkDox</span>
      <span v-else class="logo-text-mini">WD</span>
    </div>
    <el-menu
      :default-active="activeMenu"
      :collapse="isCollapsed"
      background-color="#001529"
      text-color="#ffffffa6"
      active-text-color="#fff"
      router
      @select="(index: string) => $emit('navigate', index)"
    >
      <el-menu-item index="/">
        <el-icon><HomeFilled /></el-icon>
        <span>工作台</span>
      </el-menu-item>
      <el-menu-item index="/documents">
        <el-icon><Folder /></el-icon>
        <span>文档中心</span>
      </el-menu-item>
      <el-menu-item index="/matters">
        <el-icon><Briefcase /></el-icon>
        <span>业务事项</span>
      </el-menu-item>
      <el-menu-item index="/tasks">
        <el-icon><List /></el-icon>
        <span>待办中心</span>
      </el-menu-item>
      <el-menu-item index="/task-mgmt">
        <el-icon><Finished /></el-icon>
        <span>任务管理</span>
      </el-menu-item>
      <el-menu-item index="/workflow/templates" v-if="isDeptLeader || isAdmin">
        <el-icon><Connection /></el-icon>
        <span>流程模板</span>
      </el-menu-item>
      <div class="menu-separator" v-if="isAdmin"></div>
      <el-sub-menu index="admin" v-if="isAdmin">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>系统管理</span>
        </template>
        <el-menu-item index="/admin/users">用户管理</el-menu-item>
        <el-menu-item index="/admin/roles">角色管理</el-menu-item>
        <el-menu-item index="/admin/departments">部门管理</el-menu-item>
        <el-menu-item index="/admin/document-categories">文档分类</el-menu-item>
        <el-menu-item index="/admin/tags">标签管理</el-menu-item>
        <el-menu-item index="/admin/matter-types">事项类型</el-menu-item>
      </el-sub-menu>
      <el-menu-item index="/audit" v-if="canViewAuditLogs">
        <el-icon><Document /></el-icon>
        <span>操作日志</span>
      </el-menu-item>
      <el-menu-item index="/ai/chat">
        <el-icon><ChatDotRound /></el-icon>
        <span>AI 助手</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

defineProps<{ isCollapsed: boolean }>()
defineEmits<{ navigate: [index: string] }>()

const route = useRoute()
const authStore = useAuthStore()

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/admin')) return path
  if (path.startsWith('/matters')) return '/matters'
  if (path.startsWith('/documents')) return '/documents'
  if (path.startsWith('/workflow')) return '/workflow/templates'
  if (path.startsWith('/task-mgmt')) return '/task-mgmt'
  return path
})

const isAdmin = computed(() => authStore.isAdmin)
const isDeptLeader = computed(() => authStore.isDeptLeader)
const canViewAuditLogs = computed(() => authStore.isAdmin || authStore.isDeptLeader)
</script>

<style scoped>
.sidebar {
  height: 100%;
}
.logo {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.logo-img {
  width: 32px;
  height: 32px;
  margin-right: 8px;
}
.logo-text-mini {
  font-size: 16px;
  font-weight: 700;
}
.menu-separator {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin: 8px 16px;
}
.el-menu {
  border-right: none;
}
</style>

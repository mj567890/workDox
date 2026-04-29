import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/dashboard',
    name: 'PublicDashboard',
    component: () => import('@/views/dashboard/PublicDashboardView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Workbench',
        component: () => import('@/views/home/WorkbenchView.vue'),
      },
      {
        path: 'documents',
        name: 'DocumentCenter',
        component: () => import('@/views/documents/DocumentCenterView.vue'),
      },
      {
        path: 'documents/:id',
        name: 'DocumentDetail',
        component: () => import('@/views/documents/DocumentDetailView.vue'),
      },
      {
        path: 'matters',
        name: 'MatterList',
        component: () => import('@/views/matters/MatterListView.vue'),
      },
      {
        path: 'matters/:id',
        name: 'MatterDetail',
        component: () => import('@/views/matters/MatterDetailView.vue'),
      },
      {
        path: 'workflow/templates',
        name: 'WorkflowTemplates',
        component: () => import('@/views/workflow/WorkflowTemplateListView.vue'),
      },
      {
        path: 'workflow/templates/new',
        name: 'WorkflowTemplateNew',
        component: () => import('@/views/workflow/WorkflowTemplateEditView.vue'),
        meta: { roles: ['admin', 'dept_leader'] },
      },
      {
        path: 'workflow/templates/:id/edit',
        name: 'WorkflowTemplateEdit',
        component: () => import('@/views/workflow/WorkflowTemplateEditView.vue'),
        meta: { roles: ['admin', 'dept_leader'] },
      },
      {
        path: 'tasks',
        name: 'TaskCenter',
        component: () => import('@/views/tasks/TaskCenterView.vue'),
      },
      {
        path: 'search',
        name: 'SearchResults',
        component: () => import('@/views/search/SearchResultsView.vue'),
      },
      {
        path: 'admin/users',
        name: 'UserManagement',
        component: () => import('@/views/admin/UserManagementView.vue'),
        meta: { roles: ['admin'] },
      },
      {
        path: 'admin/roles',
        name: 'RoleManagement',
        component: () => import('@/views/admin/RoleManagementView.vue'),
        meta: { roles: ['admin'] },
      },
      {
        path: 'admin/departments',
        name: 'DepartmentManagement',
        component: () => import('@/views/admin/DepartmentManagementView.vue'),
        meta: { roles: ['admin'] },
      },
      {
        path: 'admin/document-categories',
        name: 'DocumentCategoryManagement',
        component: () => import('@/views/admin/DocumentCategoryManagementView.vue'),
        meta: { roles: ['admin'] },
      },
      {
        path: 'admin/tags',
        name: 'TagManagement',
        component: () => import('@/views/admin/TagManagementView.vue'),
        meta: { roles: ['admin'] },
      },
      {
        path: 'admin/matter-types',
        name: 'MatterTypeManagement',
        component: () => import('@/views/admin/MatterTypeManagementView.vue'),
        meta: { roles: ['admin'] },
      },
      {
        path: 'audit',
        name: 'AuditLogs',
        component: () => import('@/views/audit/AuditLogView.vue'),
        meta: { roles: ['admin', 'dept_leader'] },
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/profile/ProfileView.vue'),
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/profile/SettingsView.vue'),
      },
      {
        path: 'webhooks',
        name: 'WebhookManagement',
        component: () => import('@/views/profile/WebhookManagementView.vue'),
      },
      {
        path: 'ai/chat',
        name: 'AIChat',
        component: () => import('@/views/ai/AIChatView.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const token = localStorage.getItem('token')

  // Redirect away from login page if already authenticated
  if (to.path === '/login') {
    if (token) {
      next('/')
    } else {
      next()
    }
    return
  }

  // Allow other public routes that don't require auth
  if (to.meta.requiresAuth === false) {
    next()
    return
  }

  // Authentication required but no token
  if (!token) {
    next('/login')
    return
  }

  // Authenticated — ensure user info is loaded
  const authStore = useAuthStore()
  if (!authStore.user) {
    await authStore.fetchUser()
    // If still null, fetchUser failed and its catch handler called logout(),
    // which already navigates to /login — do not call next()
    if (!authStore.user) {
      return
    }
  }

  // Role-based access control
  const requiredRoles = to.meta.roles as string[] | undefined
  if (requiredRoles && requiredRoles.length > 0) {
    const hasAccess = requiredRoles.some(role => authStore.userRoles.includes(role))
    if (!hasAccess) {
      ElMessage.warning('您没有访问此页面的权限')
      next('/')
      return
    }
  }

  next()
})

export default router

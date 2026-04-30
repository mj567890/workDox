import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermission() {
  const authStore = useAuthStore()

  const canEditDocument = computed(() =>
    authStore.isAdmin || authStore.isDeptLeader
  )

  const canDeleteDocument = computed(() =>
    authStore.isAdmin || authStore.isDeptLeader
  )

  const canLockDocument = computed(() =>
    authStore.isAdmin || authStore.isDeptLeader
  )

  const canSetOfficialVersion = computed(() =>
    authStore.isAdmin || authStore.isDeptLeader
  )

  const canViewDashboard = computed(() =>
    authStore.isAdmin || authStore.isDeptLeader
  )

  const canManageUsers = computed(() => authStore.isAdmin)
  const canManageRoles = computed(() => authStore.isAdmin)
  const canViewAuditLogs = computed(() => authStore.isAdmin || authStore.isDeptLeader)

  return {
    canEditDocument,
    canDeleteDocument,
    canLockDocument,
    canSetOfficialVersion,
    canViewDashboard,
    canManageUsers,
    canManageRoles,
    canViewAuditLogs,
  }
}

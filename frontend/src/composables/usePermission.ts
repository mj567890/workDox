import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermission() {
  const authStore = useAuthStore()

  const canEditDocument = computed(() =>
    authStore.isAdmin || authStore.isDeptLeader || authStore.isMatterOwner
  )

  const canDeleteDocument = computed(() =>
    authStore.isAdmin || authStore.isDeptLeader || authStore.isMatterOwner
  )

  const canLockDocument = computed(() =>
    authStore.isAdmin || authStore.isDeptLeader || authStore.isMatterOwner
  )

  const canSetOfficialVersion = computed(() =>
    authStore.isAdmin || authStore.isDeptLeader || authStore.isMatterOwner
  )

  const canCreateMatter = computed(() =>
    authStore.isAdmin || authStore.isDeptLeader || authStore.isMatterOwner
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
    canCreateMatter,
    canViewDashboard,
    canManageUsers,
    canManageRoles,
    canViewAuditLogs,
  }
}

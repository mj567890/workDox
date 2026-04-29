import { useAuthStore } from '@/stores/auth'
import { computed } from 'vue'

export function useAuth() {
  const authStore = useAuthStore()
  return {
    user: computed(() => authStore.user),
    isAuthenticated: computed(() => authStore.isAuthenticated),
    isAdmin: computed(() => authStore.isAdmin),
    isDeptLeader: computed(() => authStore.isDeptLeader),
    hasRole: (role: string) => authStore.hasRole(role),
    login: authStore.login,
    logout: authStore.logout,
  }
}

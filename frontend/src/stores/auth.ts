import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserInfo } from '@/api/auth'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<UserInfo | null>(null)
  const isAuthenticated = computed(() => !!token.value)

  const userRoles = computed(() => user.value?.roles.map(r => r.role_code) || [])
  const isAdmin = computed(() => userRoles.value.includes('admin'))
  const isDeptLeader = computed(() => userRoles.value.includes('dept_leader'))
  const isMatterOwner = computed(() => userRoles.value.includes('matter_owner'))

  function hasRole(roleCode: string): boolean {
    return userRoles.value.includes(roleCode)
  }

  async function login(username: string, password: string) {
    const res = await authApi.login({ username, password })
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)
    await fetchUser()
  }

  async function fetchUser() {
    try {
      user.value = await authApi.getMe()
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    router.push('/login')
  }

  return {
    token,
    user,
    isAuthenticated,
    userRoles,
    isAdmin,
    isDeptLeader,
    isMatterOwner,
    hasRole,
    login,
    fetchUser,
    logout,
  }
})

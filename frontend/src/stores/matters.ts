import { defineStore } from 'pinia'
import { ref } from 'vue'
import { mattersApi, type MatterItem, type MatterDetail, type MatterComment } from '@/api/matters'

export const useMatterStore = defineStore('matters', () => {
  const matters = ref<MatterItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentMatter = ref<MatterDetail | null>(null)
  const comments = ref<MatterComment[]>([])

  async function fetchMatters(params?: Record<string, any>) {
    loading.value = true
    try {
      const res = await mattersApi.getList(params)
      matters.value = res.items
      total.value = res.total
      return res
    } finally {
      loading.value = false
    }
  }

  async function fetchMatter(id: number) {
    currentMatter.value = await mattersApi.getDetail(id)
    return currentMatter.value
  }

  async function createMatter(data: Record<string, any>) {
    return await mattersApi.create(data)
  }

  async function updateMatter(id: number, data: Record<string, any>) {
    const updated = await mattersApi.update(id, data)
    if (currentMatter.value?.id === id) {
      Object.assign(currentMatter.value, updated)
    }
    return updated
  }

  async function deleteMatter(id: number) {
    await mattersApi.delete(id)
  }

  async function addMembers(matterId: number, userIds: number[]) {
    await mattersApi.addMembers(matterId, { user_ids: userIds })
    if (currentMatter.value?.id === matterId) {
      await fetchMatter(matterId)
    }
  }

  async function removeMember(matterId: number, userId: number) {
    await mattersApi.removeMember(matterId, userId)
    if (currentMatter.value?.id === matterId) {
      await fetchMatter(matterId)
    }
  }

  async function fetchComments(matterId: number, params?: Record<string, any>) {
    const res = await mattersApi.getComments(matterId, params)
    comments.value = res.items
    return res
  }

  async function addComment(matterId: number, content: string) {
    return await mattersApi.addComment(matterId, { content })
  }

  return {
    matters,
    total,
    loading,
    currentMatter,
    comments,
    fetchMatters,
    fetchMatter,
    createMatter,
    updateMatter,
    deleteMatter,
    addMembers,
    removeMember,
    fetchComments,
    addComment,
  }
})

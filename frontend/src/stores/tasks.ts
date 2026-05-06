import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tasksApi, type TaskItem } from '@/api/tasks'

export const useTaskStore = defineStore('tasks', () => {
  const tasks = ref<TaskItem[]>([])
  const total = ref(0)
  const loading = ref(false)

  async function fetchTasks(params?: Record<string, any>) {
    loading.value = true
    try {
      const res = await tasksApi.getList(params)
      tasks.value = res.items
      total.value = res.total
      return res
    } finally {
      loading.value = false
    }
  }

  async function updateTask(id: number, data: Record<string, any>) {
    return await tasksApi.update(id, data)
  }

  return { tasks, total, loading, fetchTasks, updateTask }
})

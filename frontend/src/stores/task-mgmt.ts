import { defineStore } from 'pinia'
import { ref } from 'vue'
import { taskTemplatesApi, type TemplateItem } from '@/api/task-templates'
import { taskInstancesApi, type TaskItem, type BoardData } from '@/api/task-instances'

export const useTaskMgmtStore = defineStore('task-mgmt', () => {
  const templates = ref<TemplateItem[]>([])
  const tasks = ref<TaskItem[]>([])
  const currentBoard = ref<BoardData | null>(null)
  const loading = ref(false)

  async function fetchTemplates(category?: string) {
    loading.value = true
    try {
      const res = await taskTemplatesApi.getList(category)
      templates.value = res.items
    } finally {
      loading.value = false
    }
  }

  async function createTemplate(data: any) {
    const tpl = await taskTemplatesApi.create(data)
    templates.value.push(tpl)
    return tpl
  }

  async function deleteTemplate(id: number) {
    await taskTemplatesApi.delete(id)
    templates.value = templates.value.filter(t => t.id !== id)
  }

  async function cloneTemplate(id: number) {
    const tpl = await taskTemplatesApi.clone(id)
    templates.value.push(tpl)
    return tpl
  }

  async function fetchTasks(status?: string) {
    loading.value = true
    try {
      const res = await taskInstancesApi.getList(status)
      tasks.value = res.items
    } finally {
      loading.value = false
    }
  }

  async function createTask(data: { template_id: number; title?: string }) {
    const task = await taskInstancesApi.create(data)
    tasks.value.unshift(task)
    return task
  }

  async function deleteTask(id: number) {
    await taskInstancesApi.delete(id)
    tasks.value = tasks.value.filter(t => t.id !== id)
  }

  async function fetchBoard(taskId: number) {
    currentBoard.value = await taskInstancesApi.getBoard(taskId)
    return currentBoard.value
  }

  return {
    templates, tasks, currentBoard, loading,
    fetchTemplates, createTemplate, deleteTemplate, cloneTemplate,
    fetchTasks, createTask, deleteTask, fetchBoard,
  }
})

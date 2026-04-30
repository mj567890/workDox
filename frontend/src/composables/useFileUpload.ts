import { ref } from 'vue'
import { ElMessage } from 'element-plus'

export function useFileUpload(options?: {
  maxSize?: number
  allowedTypes?: string[]
  onProgress?: (percent: number) => void
}) {
  const uploading = ref(false)
  const progress = ref(0)

  async function upload(files: File[], categoryId?: number) {
    uploading.value = true
    progress.value = 0
    const results = []

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        if (options?.maxSize && file.size > options.maxSize) {
          ElMessage.warning(`文件 ${file.name} 超过大小限制`)
          continue
        }

        const formData = new FormData()
        formData.append('file', file)
        if (categoryId) formData.append('category_id', String(categoryId))

        const { documentsApi } = await import('@/api/documents')
        const result = await documentsApi.upload(formData)
        results.push(result)
        progress.value = Math.round(((i + 1) / files.length) * 100)
        options?.onProgress?.(progress.value)
      }
      return results
    } finally {
      uploading.value = false
    }
  }

  return { uploading, progress, upload }
}

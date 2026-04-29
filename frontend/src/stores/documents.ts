import { defineStore } from 'pinia'
import { ref } from 'vue'
import { documentsApi, type DocumentItem, type DocumentVersion, type CategoryItem, type TagItem, type PaginatedResponse, type LockStatus } from '@/api/documents'

export const useDocumentStore = defineStore('documents', () => {
  const documents = ref<DocumentItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const currentDocument = ref<DocumentItem | null>(null)
  const versions = ref<DocumentVersion[]>([])
  const categories = ref<CategoryItem[]>([])
  const tags = ref<TagItem[]>([])
  const lockStatus = ref<LockStatus | null>(null)

  async function fetchDocuments(params?: Record<string, any>) {
    loading.value = true
    try {
      const res = await documentsApi.getList(params)
      documents.value = res.items
      total.value = res.total
      return res
    } finally {
      loading.value = false
    }
  }

  async function fetchDocument(id: number) {
    currentDocument.value = await documentsApi.getDetail(id)
    return currentDocument.value
  }

  async function uploadDocument(formData: FormData) {
    return await documentsApi.upload(formData)
  }

  async function deleteDocument(id: number) {
    await documentsApi.delete(id)
  }

  async function fetchVersions(id: number) {
    versions.value = await documentsApi.getVersions(id)
  }

  async function uploadVersion(id: number, formData: FormData) {
    const version = await documentsApi.uploadVersion(id, formData)
    await fetchVersions(id)
    return version
  }

  async function setOfficialVersion(docId: number, versionId: number) {
    await documentsApi.setOfficialVersion(docId, versionId)
    await fetchVersions(docId)
  }

  async function lockDocument(id: number) {
    lockStatus.value = await documentsApi.lock(id)
    return lockStatus.value
  }

  async function unlockDocument(id: number) {
    await documentsApi.unlock(id)
    lockStatus.value = null
  }

  async function fetchLockStatus(id: number) {
    lockStatus.value = await documentsApi.getLockStatus(id)
  }

  async function fetchCategories() {
    categories.value = await documentsApi.getCategories()
  }

  async function fetchTags() {
    tags.value = await documentsApi.getTags()
  }

  async function createTag(data: { name: string; color?: string }) {
    const tag = await documentsApi.createTag(data)
    await fetchTags()
    return tag
  }

  async function deleteTag(id: number) {
    await documentsApi.deleteTag(id)
    await fetchTags()
  }

  return {
    documents,
    total,
    loading,
    currentDocument,
    versions,
    categories,
    tags,
    lockStatus,
    fetchDocuments,
    fetchDocument,
    uploadDocument,
    deleteDocument,
    fetchVersions,
    uploadVersion,
    setOfficialVersion,
    lockDocument,
    unlockDocument,
    fetchLockStatus,
    fetchCategories,
    fetchTags,
    createTag,
    deleteTag,
  }
})

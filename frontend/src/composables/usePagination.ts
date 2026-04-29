import { ref, computed } from 'vue'

export function usePagination(initialPage = 1, initialPageSize = 20) {
  const page = ref(initialPage)
  const pageSize = ref(initialPageSize)
  const total = ref(0)

  const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 0)

  function setPage(p: number) {
    page.value = p
  }

  function setPageSize(size: number) {
    pageSize.value = size
    page.value = 1
  }

  function setTotal(t: number) {
    total.value = t
  }

  return { page, pageSize, total, totalPages, setPage, setPageSize, setTotal }
}

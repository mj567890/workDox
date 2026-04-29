import { ref, computed } from 'vue'

export function useBatchSelection<T extends { id: number }>() {
  const selectedIds = ref<Set<number>>(new Set())

  const selectedCount = computed(() => selectedIds.value.size)
  const hasSelection = computed(() => selectedIds.value.size > 0)

  function toggleSelection(id: number) {
    const newSet = new Set(selectedIds.value)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    selectedIds.value = newSet
  }

  function selectAll(items: T[]) {
    selectedIds.value = new Set(items.map(i => i.id))
  }

  function clearSelection() {
    selectedIds.value = new Set()
  }

  function isSelected(id: number): boolean {
    return selectedIds.value.has(id)
  }

  return { selectedIds, selectedCount, hasSelection, toggleSelection, selectAll, clearSelection, isSelected }
}

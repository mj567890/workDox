import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

export function useShortcuts() {
  const router = useRouter()

  function handleKeydown(e: KeyboardEvent) {
    // If focus is on an input/textarea/select, don't process most shortcuts
    // Ctrl+K and Esc are exceptions
    const tag = (e.target as HTMLElement)?.tagName
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'

    // Ctrl+K - Focus global search (always trigger)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault()
      // Try to find the search input by class first, then by id
      const searchInput = document.querySelector('.global-search-input') as HTMLInputElement | null
        ?? document.querySelector('#global-search') as HTMLInputElement | null
      if (searchInput) {
        searchInput.focus()
      } else {
        // Dispatch custom event so components can react
        window.dispatchEvent(new CustomEvent('global-search-focus'))
      }
      return
    }

    // Esc - Close el-dialog (always allow, but don't interfere with native handling)
    if (e.key === 'Escape') {
      // Element Plus dialogs handle Escape natively via their own event listeners.
      // We only intervene if there's a dialog element visible.
      const dialogOverlays = document.querySelectorAll('.el-overlay')
      if (dialogOverlays.length > 0) {
        // Find the topmost visible dialog and close it programmatically
        const topOverlay = dialogOverlays[dialogOverlays.length - 1]
        // Let Element Plus handle it natively via its built-in close logic
        // by dispatching a keydown with Escape on the overlay
        const escEvent = new KeyboardEvent('keydown', {
          key: 'Escape',
          code: 'Escape',
          keyCode: 27,
          bubbles: true,
        })
        topOverlay.dispatchEvent(escEvent)
      }
      return
    }

    // If focus is in an input area, skip the following shortcuts
    if (isInput) return

    // Ctrl+N - Navigate to task management page
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
      e.preventDefault()
      router.push('/task-mgmt')
      return
    }

    // Ctrl+B - Toggle sidebar collapse
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
      e.preventDefault()
      window.dispatchEvent(new CustomEvent('toggle-sidebar'))
      return
    }

    // ? (Shift+/) - Show keyboard shortcuts help panel
    if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
      window.dispatchEvent(new CustomEvent('show-shortcuts-help'))
      return
    }
  }

  onMounted(() => window.addEventListener('keydown', handleKeydown))
  onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
}

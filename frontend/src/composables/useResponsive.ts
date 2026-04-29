import { ref, computed, onMounted, onUnmounted } from 'vue'

export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

const breakpoints: Record<Breakpoint, number> = {
  xs: 0,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
}

const width = ref(window.innerWidth)
const breakpoint = ref<Breakpoint>(getBreakpoint(window.innerWidth))

function getBreakpoint(w: number): Breakpoint {
  if (w >= breakpoints.xl) return 'xl'
  if (w >= breakpoints.lg) return 'lg'
  if (w >= breakpoints.md) return 'md'
  if (w >= breakpoints.sm) return 'sm'
  return 'xs'
}

function update() {
  width.value = window.innerWidth
  breakpoint.value = getBreakpoint(window.innerWidth)
}

let listeners = 0

export function useResponsive() {
  const isMobile = computed(() => breakpoint.value === 'xs' || breakpoint.value === 'sm')
  const isTablet = computed(() => breakpoint.value === 'md')
  const isDesktop = computed(() => breakpoint.value === 'lg' || breakpoint.value === 'xl')

  onMounted(() => {
    if (listeners === 0) {
      window.addEventListener('resize', update)
    }
    listeners++
  })

  onUnmounted(() => {
    listeners--
    if (listeners <= 0) {
      window.removeEventListener('resize', update)
      listeners = 0
    }
  })

  return {
    width,
    breakpoint,
    isMobile,
    isTablet,
    isDesktop,
  }
}

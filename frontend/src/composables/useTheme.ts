import { ref, watch } from 'vue'

const isDark = ref(false)

export function useTheme() {
  // 初始化
  const saved = localStorage.getItem('theme')
  isDark.value = saved === 'dark'
  applyTheme(isDark.value)

  watch(isDark, (val) => {
    applyTheme(val)
    localStorage.setItem('theme', val ? 'dark' : 'light')
  })

  function applyTheme(dark: boolean) {
    if (dark) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  function toggleTheme() {
    isDark.value = !isDark.value
  }

  return { isDark, toggleTheme }
}

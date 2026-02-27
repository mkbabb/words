import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { Themes, DEFAULT_THEME, type Theme } from '@/stores/types/constants'

/**
 * Streamlined UIStore focused on shared UI state
 * Handles theme and sidebar management only
 * Mode-specific functionality accessed directly from mode stores
 */
export const useUIStore = defineStore('ui', () => {
  // ==========================================================================
  // SHARED UI STATE
  // ==========================================================================

  // Theme and appearance
  const theme = ref<Theme>(DEFAULT_THEME)

  // Sidebar visibility
  const sidebarOpen = ref(false)
  const sidebarCollapsed = ref(true)

  // ==========================================================================
  // COMPUTED
  // ==========================================================================

  const resolvedTheme = computed((): 'light' | 'dark' => {
    if (theme.value === Themes.SYSTEM) {
      if (typeof window !== 'undefined' && window.matchMedia) {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      }
      return 'light'
    }
    return theme.value as 'light' | 'dark'
  })

  // ==========================================================================
  // SHARED ACTIONS
  // ==========================================================================

  // Theme management
  const toggleTheme = () => {
    const themes: Theme[] = [Themes.LIGHT, Themes.DARK, Themes.SYSTEM]
    const currentIndex = themes.indexOf(theme.value)
    theme.value = themes[(currentIndex + 1) % themes.length]
  }

  const setTheme = (newTheme: Theme) => {
    theme.value = newTheme
  }

  // Sidebar management
  const toggleSidebar = () => {
    sidebarOpen.value = !sidebarOpen.value
  }

  const setSidebarOpen = (open: boolean) => {
    sidebarOpen.value = open
  }

  const setSidebarCollapsed = (collapsed: boolean) => {
    sidebarCollapsed.value = collapsed
  }

  const toggleSidebarCollapsed = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  // ==========================================================================
  // RESET
  // ==========================================================================

  const resetUI = () => {
    theme.value = DEFAULT_THEME
    sidebarOpen.value = false
    sidebarCollapsed.value = true
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================

  return {
    // Shared State
    theme,
    resolvedTheme,
    sidebarOpen,
    sidebarCollapsed,

    // Shared Actions
    toggleTheme,
    setTheme,
    toggleSidebar,
    setSidebarOpen,
    setSidebarCollapsed,
    toggleSidebarCollapsed,

    // Reset
    resetUI,
  }
}, {
  persist: {
    key: 'ui-state',
    pick: [
      'theme',
      'sidebarOpen',
      'sidebarCollapsed',
    ]
  }
})

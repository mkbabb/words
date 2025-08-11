import { computed } from 'vue'
import { usePersistedState } from './usePersistedState'

export type Theme = 'light' | 'dark' | 'system'

interface UIState {
  theme: Theme
  sidebarOpen: boolean
  sidebarCollapsed: boolean
}

const DEFAULT_UI_STATE: UIState = {
  theme: 'system',
  sidebarOpen: false,
  sidebarCollapsed: true
}

/**
 * useUIState composable - Lightweight UI state management
 * Replaces the Pinia UIStore with persisted state using StateProvider
 */
export function useUIState() {
  const [state] = usePersistedState<UIState>('ui-state', DEFAULT_UI_STATE, {
    version: 1,
    syncable: true, // UI preferences should sync across devices
    immediate: true
  })
  
  // Theme management
  const toggleTheme = () => {
    const themes: Theme[] = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(state.value.theme)
    state.value.theme = themes[(currentIndex + 1) % themes.length]
  }
  
  const setTheme = (theme: Theme) => {
    state.value.theme = theme
  }
  
  // Computed for actual theme (resolving 'system')
  const resolvedTheme = computed(() => {
    if (state.value.theme === 'system') {
      // Check system preference
      if (typeof window !== 'undefined' && window.matchMedia) {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      }
      return 'light'
    }
    return state.value.theme
  })
  
  // Sidebar management
  const toggleSidebar = () => {
    state.value.sidebarOpen = !state.value.sidebarOpen
  }
  
  const setSidebarOpen = (open: boolean) => {
    state.value.sidebarOpen = open
  }
  
  const setSidebarCollapsed = (collapsed: boolean) => {
    state.value.sidebarCollapsed = collapsed
  }
  
  const toggleSidebarCollapsed = () => {
    state.value.sidebarCollapsed = !state.value.sidebarCollapsed
  }
  
  // Reset to defaults
  const resetUI = () => {
    state.value = { ...DEFAULT_UI_STATE }
  }
  
  return {
    // State
    theme: computed(() => state.value.theme),
    resolvedTheme,
    sidebarOpen: computed(() => state.value.sidebarOpen),
    sidebarCollapsed: computed(() => state.value.sidebarCollapsed),
    
    // Actions
    toggleTheme,
    setTheme,
    toggleSidebar,
    setSidebarOpen,
    setSidebarCollapsed,
    toggleSidebarCollapsed,
    resetUI
  }
}
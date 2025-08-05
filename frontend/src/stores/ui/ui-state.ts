import { defineStore } from 'pinia'
import { ref, readonly } from 'vue'
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
  // SHARED ACTIONS
  // ==========================================================================
  
  // Theme management
  const toggleTheme = () => {
    theme.value = theme.value === Themes.LIGHT ? Themes.DARK : Themes.LIGHT
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
  
  
  // ==========================================================================
  // RESET
  // ==========================================================================
  
  const resetUI = () => {
    // Reset shared state only
    theme.value = DEFAULT_THEME
    sidebarOpen.value = false
    sidebarCollapsed.value = true
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // Shared State
    theme: readonly(theme),
    sidebarOpen: readonly(sidebarOpen),
    sidebarCollapsed: readonly(sidebarCollapsed),
    
    
    // Shared Actions
    toggleTheme,
    setTheme,
    toggleSidebar,
    setSidebarOpen,
    setSidebarCollapsed,
    
    
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
      // Note: Mode-specific UI states handle their own persistence
    ]
  }
})
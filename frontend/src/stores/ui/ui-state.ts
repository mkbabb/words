import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * Streamlined UIStore focused on shared UI state.
 * Theme / dark-mode is managed by glass-ui's useGlobalDark — see App.vue.
 * This store handles sidebar state only.
 */
export const useUIStore = defineStore('ui', () => {
  // ==========================================================================
  // SHARED UI STATE
  // ==========================================================================

  // Sidebar visibility
  const sidebarOpen = ref(false)
  const sidebarCollapsed = ref(true)

  // ==========================================================================
  // SHARED ACTIONS
  // ==========================================================================

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
    sidebarOpen.value = false
    sidebarCollapsed.value = true
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================

  return {
    // Shared State
    sidebarOpen,
    sidebarCollapsed,

    // Shared Actions
    toggleSidebar,
    setSidebarOpen,
    setSidebarCollapsed,
    toggleSidebarCollapsed,

    // Reset
    resetUI,
  }
})

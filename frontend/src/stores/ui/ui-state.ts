import { defineStore } from 'pinia'
import { ref, readonly, computed } from 'vue'
import { useSearchConfigStore } from '../search/search-config'
import { useLookupMode } from '../search/modes/lookup'
import type { SearchMode } from '@/types'
import { Themes, DEFAULT_THEME, type Theme } from '@/stores/types/constants'

/**
 * Refactored UIStore with mode-specific encapsulation
 * Handles theme, sidebar, and mode-specific UI preferences
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
  // MODE-SPECIFIC UI STATES
  // ==========================================================================
  
  const lookupMode = useLookupMode()
  // Future: Add wordlistUI, wordOfTheDayUI, stageUI as needed
  
  // Mode UI registry
  const modeUIStates = {
    lookup: lookupMode,
    wordlist: null, // No specific UI state for wordlist yet
    'word-of-the-day': null, // No specific UI state for WOTD yet
    stage: null, // No specific UI state for stage yet
  }
  
  // ==========================================================================
  // COMPUTED PROPERTIES
  // ==========================================================================
  
  const searchConfig = useSearchConfigStore()
  const currentMode = computed(() => searchConfig.searchMode)
  
  // Get current mode's UI state
  const currentModeUIState = computed(() => {
    return modeUIStates[currentMode.value]
  })
  
  // Legacy computed for backward compatibility
  const mode = computed(() => searchConfig.lookupSubMode)
  
  // Expose mode-specific properties based on current mode
  const selectedCardVariant = computed(() => 
    currentMode.value === 'lookup' ? lookupMode.selectedCardVariant.value : 'default'
  )
  
  const pronunciationMode = computed(() => 
    currentMode.value === 'lookup' ? lookupMode.pronunciationMode.value : 'phonetic'
  )
  
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
  // MODE TRANSITION HANDLING
  // ==========================================================================
  
  const handleModeChange = async (newMode: SearchMode, previousMode: SearchMode) => {
    console.log('🔄 UI handling mode change:', previousMode, '->', newMode)
    
    // Execute exit handler for previous mode
    const previousModeUI = modeUIStates[previousMode]
    if (previousModeUI?.handler?.onExit) {
      await previousModeUI.handler.onExit(newMode)
    }
    
    // Execute enter handler for new mode
    const newModeUI = modeUIStates[newMode]
    if (newModeUI?.handler?.onEnter) {
      await newModeUI.handler.onEnter(previousMode)
    }
  }
  
  // ==========================================================================
  // MODE-SPECIFIC ACTION DELEGATES
  // ==========================================================================
  
  // Lookup mode UI actions
  const setCardVariant = (variant: 'default' | 'gold' | 'silver' | 'bronze') => {
    if (currentMode.value === 'lookup') {
      lookupMode.setCardVariant(variant)
    }
  }
  
  const cycleCardVariant = () => {
    if (currentMode.value === 'lookup') {
      lookupMode.cycleCardVariant()
    }
  }
  
  const togglePronunciation = () => {
    if (currentMode.value === 'lookup') {
      lookupMode.togglePronunciation()
    }
  }
  
  const setPronunciationMode = (mode: 'phonetic' | 'ipa') => {
    if (currentMode.value === 'lookup') {
      lookupMode.setPronunciationMode(mode)
    }
  }
  
  // ==========================================================================
  // RESET
  // ==========================================================================
  
  const resetUI = () => {
    // Reset shared state
    theme.value = DEFAULT_THEME
    sidebarOpen.value = false
    sidebarCollapsed.value = true
    
    // Reset mode-specific states
    lookupMode.reset()
    // Future: Reset other mode UI states
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // Shared State
    theme: readonly(theme),
    sidebarOpen: readonly(sidebarOpen),
    sidebarCollapsed: readonly(sidebarCollapsed),
    
    // Mode-Specific State (computed based on current mode)
    selectedCardVariant: readonly(selectedCardVariant),
    pronunciationMode: readonly(pronunciationMode),
    
    // Legacy compatibility
    mode: readonly(mode),
    
    // Shared Actions
    toggleTheme,
    setTheme,
    toggleSidebar,
    setSidebarOpen,
    setSidebarCollapsed,
    
    // Mode-Specific Actions (delegates)
    setCardVariant,
    cycleCardVariant,
    togglePronunciation,
    setPronunciationMode,
    
    // Mode handling
    handleModeChange,
    
    // Reset
    resetUI,
    
    // Expose mode UI states for advanced usage
    lookupMode,
    currentModeUIState,
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
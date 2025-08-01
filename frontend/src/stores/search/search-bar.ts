import { defineStore } from 'pinia'
import { ref, computed, nextTick, readonly } from 'vue'
import { useAIMode } from '../composables/useAIMode'

/**
 * SearchBarStore - Pure UI state and interactions for the search bar
 * Handles dropdown visibility, focus state, autocomplete, and AI indicators
 */
export const useSearchBarStore = defineStore('searchBar', () => {
  // ==========================================================================
  // UI STATE (Non-persisted)
  // ==========================================================================
  
  // Dropdown and selection state
  const showSearchResults = ref(false)
  const searchSelectedIndex = ref(0)
  
  // Focus management
  const isSearchBarFocused = ref(false)
  
  // Control visibility
  const showSearchControls = ref(false)
  
  // Animation and feedback states
  const showErrorAnimation = ref(false)
  const isSwitchingModes = ref(false)
  
  // Autocomplete and suggestions
  const autocompleteText = ref('')
  const aiSuggestions = ref<string[]>([])
  
  // Operation flags
  const isDirectLookup = ref(false)
  
  // Current query (non-persisted - router handles persistence)
  const searchQuery = ref('')
  
  // Mode-specific queries for switching contexts
  const modeQueries = ref({
    lookup: '',
    wordlist: '',
    wordOfTheDay: '',
    stage: '',
  })

  // ==========================================================================
  // AI MODE INTEGRATION
  // ==========================================================================
  
  // Use the AI mode composable for reactive AI detection
  const { isAIQuery, showSparkle, enableAIMode, disableAIMode } = useAIMode(searchQuery)

  // ==========================================================================
  // COMPUTED PROPERTIES
  // ==========================================================================
  
  // Combined search bar state for easy access
  const searchBarState = computed(() => ({
    query: searchQuery.value,
    showResults: showSearchResults.value,
    selectedIndex: searchSelectedIndex.value,
    isFocused: isSearchBarFocused.value,
    showControls: showSearchControls.value,
    isAIQuery: isAIQuery.value,
    showSparkle: showSparkle.value,
    showErrorAnimation: showErrorAnimation.value,
    autocompleteText: autocompleteText.value,
    isDirectLookup: isDirectLookup.value,
    isSwitchingModes: isSwitchingModes.value
  }))

  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  // Query management
  const setQuery = (query: string) => {
    searchQuery.value = query
  }

  const clearQuery = () => {
    searchQuery.value = ''
  }

  // Mode query management
  const saveModeQuery = (mode: string, query: string) => {
    const modeKey = mode === 'word-of-the-day' ? 'wordOfTheDay' : mode
    modeQueries.value[modeKey as keyof typeof modeQueries.value] = query
  }

  const restoreModeQuery = (mode: string): string => {
    const modeKey = mode === 'word-of-the-day' ? 'wordOfTheDay' : mode
    return modeQueries.value[modeKey as keyof typeof modeQueries.value] || ''
  }

  // Dropdown management
  const showDropdown = () => {
    showSearchResults.value = true
  }

  const hideDropdown = () => {
    showSearchResults.value = false
    searchSelectedIndex.value = 0
  }

  const clearResults = () => {
    hideDropdown()
  }

  // Selection management
  const setSelectedIndex = (index: number) => {
    searchSelectedIndex.value = index
  }

  const selectNext = (maxResults: number) => {
    if (searchSelectedIndex.value < maxResults - 1) {
      searchSelectedIndex.value++
    }
  }

  const selectPrevious = () => {
    if (searchSelectedIndex.value > 0) {
      searchSelectedIndex.value--
    }
  }

  const resetSelection = () => {
    searchSelectedIndex.value = 0
  }

  // Focus management
  const setFocused = (focused: boolean) => {
    isSearchBarFocused.value = focused
  }

  // Control management
  const toggleControls = () => {
    showSearchControls.value = !showSearchControls.value
  }

  const hideControls = () => {
    showSearchControls.value = false
  }

  // Animation management
  const triggerErrorAnimation = () => {
    showErrorAnimation.value = true
    setTimeout(() => {
      showErrorAnimation.value = false
    }, 1000)
  }

  // Mode switching state
  const setSwitchingModes = (switching: boolean) => {
    isSwitchingModes.value = switching
    
    if (switching) {
      // Auto-reset after timeout to prevent stuck state
      setTimeout(() => {
        isSwitchingModes.value = false
      }, 2000)
    }
  }

  // Direct lookup management
  const setDirectLookup = (direct: boolean) => {
    isDirectLookup.value = direct
    
    if (direct) {
      // Auto-reset after timeout
      setTimeout(() => {
        isDirectLookup.value = false
      }, 2000)
    }
  }

  // Autocomplete management
  const setAutocomplete = (text: string) => {
    autocompleteText.value = text
  }

  const clearAutocomplete = () => {
    autocompleteText.value = ''
  }

  // AI suggestions management
  const setAISuggestions = (suggestions: string[]) => {
    aiSuggestions.value = suggestions
  }

  const clearAISuggestions = () => {
    aiSuggestions.value = []
  }

  // Combined reset for search operations
  const resetForDirectLookup = () => {
    hideDropdown()
    setDirectLookup(true)
    disableAIMode()
  }

  const resetForModeSwitch = async () => {
    hideDropdown()
    setSwitchingModes(true)
    await nextTick()
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    searchQuery: readonly(searchQuery),
    modeQueries: readonly(modeQueries),
    showSearchResults: readonly(showSearchResults),
    searchSelectedIndex: readonly(searchSelectedIndex),
    isSearchBarFocused: readonly(isSearchBarFocused),
    showSearchControls: readonly(showSearchControls),
    isAIQuery,
    showSparkle,
    showErrorAnimation: readonly(showErrorAnimation),
    isSwitchingModes: readonly(isSwitchingModes),
    autocompleteText: readonly(autocompleteText),
    aiSuggestions: readonly(aiSuggestions),
    isDirectLookup: readonly(isDirectLookup),
    
    // Computed
    searchBarState,
    
    // Actions
    setQuery,
    clearQuery,
    saveModeQuery,
    restoreModeQuery,
    showDropdown,
    hideDropdown,
    clearResults,
    setSelectedIndex,
    selectNext,
    selectPrevious,
    resetSelection,
    setFocused,
    toggleControls,
    hideControls,
    triggerErrorAnimation,
    setSwitchingModes,
    setDirectLookup,
    setAutocomplete,
    clearAutocomplete,
    setAISuggestions,
    clearAISuggestions,
    enableAIMode,
    disableAIMode,
    resetForDirectLookup,
    resetForModeSwitch
  }
})
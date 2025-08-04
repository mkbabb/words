import { defineStore } from 'pinia'
import { ref, readonly, computed } from 'vue'
import { useSearchConfigStore } from './search-config'
import { useLookupMode } from './modes/lookup'
import { useWordlistMode } from './modes/wordlist'
import type { SearchMode } from '@/types'

/**
 * Refactored SearchBarStore with mode-specific encapsulation
 * Handles search input, dropdown state, and mode-specific UI features
 */
export const useSearchBarStore = defineStore('searchBar', () => {
  // ==========================================================================
  // SHARED SEARCH BAR STATE
  // ==========================================================================
  
  const searchQuery = ref('')
  const searchSelectedIndex = ref(0)
  const showDropdown = ref(false)
  const showSearchControls = ref(false)
  const isFocused = ref(false)
  const isHovered = ref(false)
  const hasErrorAnimation = ref(false)
  const modeSwitchAnimation = ref(false)
  const isDirectLookup = ref(false)
  const autocompleteText = ref('')
  
  // ==========================================================================
  // MODE-SPECIFIC STATES
  // ==========================================================================
  
  const lookupMode = useLookupMode()
  const wordlistMode = useWordlistMode()
  
  // Mode state registry
  const modeStates = {
    lookup: lookupMode,
    wordlist: wordlistMode,
    'word-of-the-day': null, // No specific state for WOTD
    stage: null, // No specific state for stage
  }
  
  // ==========================================================================
  // COMPUTED PROPERTIES
  // ==========================================================================
  
  const searchConfig = useSearchConfigStore()
  const currentMode = computed(() => searchConfig.searchMode)
  
  // Get current mode's state
  const currentModeState = computed(() => {
    return modeStates[currentMode.value]
  })
  
  // Expose mode-specific properties based on current mode
  const isAIQuery = computed(() => 
    currentMode.value === 'lookup' ? lookupMode.isAIQuery.value : false
  )
  
  const showSparkle = computed(() => 
    currentMode.value === 'lookup' ? lookupMode.showSparkle.value : false
  )
  
  const aiSuggestions = computed(() => 
    currentMode.value === 'lookup' ? lookupMode.aiSuggestions.value : []
  )
  
  const batchMode = computed(() => 
    currentMode.value === 'wordlist' ? wordlistMode.batchMode.value : false
  )
  
  const processingQueue = computed(() => 
    currentMode.value === 'wordlist' ? wordlistMode.processingQueue.value : []
  )

  // Legacy computed properties for backward compatibility
  const showSearchResults = computed(() => showDropdown.value)
  const isSearchBarFocused = computed(() => isFocused.value)
  
  // ==========================================================================
  // SHARED ACTIONS
  // ==========================================================================
  
  const setQuery = (query: string) => {
    searchQuery.value = query
  }
  
  const clearQuery = () => {
    searchQuery.value = ''
    searchSelectedIndex.value = 0
  }
  
  const setSelectedIndex = (index: number) => {
    searchSelectedIndex.value = index
  }
  
  const toggleDropdown = () => {
    showDropdown.value = !showDropdown.value
  }
  
  const setDropdown = (show: boolean) => {
    showDropdown.value = show
  }

  const openDropdown = () => {
    showDropdown.value = true
  }

  const hideDropdown = () => {
    showDropdown.value = false
  }
  
  const toggleSearchControls = () => {
    showSearchControls.value = !showSearchControls.value
  }
  
  const setSearchControls = (show: boolean) => {
    showSearchControls.value = show
  }
  
  const setFocused = (focused: boolean) => {
    isFocused.value = focused
    if (!focused) {
      // Hide dropdown when losing focus
      showDropdown.value = false
    }
  }
  
  const setHovered = (hovered: boolean) => {
    isHovered.value = hovered
  }

  const setDirectLookup = (directLookup: boolean) => {
    isDirectLookup.value = directLookup
  }

  const setAutocompleteText = (text: string) => {
    autocompleteText.value = text
  }

  const hideControls = () => {
    showSearchControls.value = false
  }

  const resetSelection = () => {
    searchSelectedIndex.value = 0
  }
  
  const triggerErrorAnimation = () => {
    hasErrorAnimation.value = true
    setTimeout(() => {
      hasErrorAnimation.value = false
    }, 600)
  }
  
  const triggerModeSwitchAnimation = () => {
    modeSwitchAnimation.value = true
    setTimeout(() => {
      modeSwitchAnimation.value = false
    }, 400)
  }
  
  // ==========================================================================
  // MODE TRANSITION HANDLING
  // ==========================================================================
  
  const handleModeChange = async (newMode: SearchMode, previousMode: SearchMode) => {
    console.log('🔄 Search bar handling mode change:', previousMode, '->', newMode)
    
    // Trigger mode switch animation
    triggerModeSwitchAnimation()
    
    // Execute exit handler for previous mode
    const previousModeState = modeStates[previousMode]
    if (previousModeState?.handler?.onExit) {
      await previousModeState.handler.onExit(newMode)
    }
    
    // Execute enter handler for new mode
    const newModeState = modeStates[newMode]
    if (newModeState?.handler?.onEnter) {
      await newModeState.handler.onEnter(previousMode)
    }
    
    // Clear search query when switching modes (optional)
    // clearQuery()
  }
  
  // ==========================================================================
  // MODE-SPECIFIC ACTION DELEGATES
  // ==========================================================================
  
  // Lookup mode actions
  const setAIQuery = (isAI: boolean) => {
    if (currentMode.value === 'lookup') {
      lookupMode.setAIQuery(isAI)
    }
  }
  
  const setShowSparkle = (show: boolean) => {
    if (currentMode.value === 'lookup') {
      lookupMode.setShowSparkle(show)
    }
  }
  
  const setAISuggestions = (suggestions: string[]) => {
    if (currentMode.value === 'lookup') {
      lookupMode.setAISuggestions(suggestions)
    }
  }
  
  const addAISuggestion = (suggestion: string) => {
    if (currentMode.value === 'lookup') {
      lookupMode.addAISuggestion(suggestion)
    }
  }
  
  const clearAISuggestions = () => {
    if (currentMode.value === 'lookup') {
      lookupMode.clearAISuggestions()
    }
  }
  
  // Wordlist mode actions
  const toggleBatchMode = () => {
    if (currentMode.value === 'wordlist') {
      wordlistMode.toggleBatchMode()
    }
  }
  
  const setBatchMode = (enabled: boolean) => {
    if (currentMode.value === 'wordlist') {
      wordlistMode.setBatchMode(enabled)
    }
  }
  
  const addToQueue = (word: string) => {
    if (currentMode.value === 'wordlist') {
      wordlistMode.addToQueue(word)
    }
  }
  
  const addBatchToQueue = (words: string[]) => {
    if (currentMode.value === 'wordlist') {
      wordlistMode.addBatchToQueue(words)
    }
  }
  
  const removeFromQueue = (word: string) => {
    if (currentMode.value === 'wordlist') {
      wordlistMode.removeFromQueue(word)
    }
  }
  
  const clearQueue = () => {
    if (currentMode.value === 'wordlist') {
      wordlistMode.clearQueue()
    }
  }
  
  // ==========================================================================
  // RESET
  // ==========================================================================
  
  const reset = () => {
    // Reset shared state
    searchQuery.value = ''
    searchSelectedIndex.value = 0
    showDropdown.value = false
    showSearchControls.value = false
    isFocused.value = false
    isHovered.value = false
    hasErrorAnimation.value = false
    modeSwitchAnimation.value = false
    isDirectLookup.value = false
    autocompleteText.value = ''
    
    // Reset mode-specific states
    lookupMode.reset()
    wordlistMode.reset()
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // Shared State
    searchQuery: readonly(searchQuery),
    searchSelectedIndex: readonly(searchSelectedIndex),
    showDropdown: readonly(showDropdown),
    showSearchControls: readonly(showSearchControls),
    isFocused: readonly(isFocused),
    isHovered: readonly(isHovered),
    hasErrorAnimation: readonly(hasErrorAnimation),
    modeSwitchAnimation: readonly(modeSwitchAnimation),
    isDirectLookup: readonly(isDirectLookup),
    autocompleteText: readonly(autocompleteText),
    showSearchResults: readonly(showSearchResults),
    isSearchBarFocused: readonly(isSearchBarFocused),
    
    // Mode-Specific State (computed based on current mode)
    isAIQuery: readonly(isAIQuery),
    showSparkle: readonly(showSparkle),
    aiSuggestions: readonly(aiSuggestions),
    batchMode: readonly(batchMode),
    processingQueue: readonly(processingQueue),
    
    // Shared Actions
    setQuery,
    clearQuery,
    setSelectedIndex,
    toggleDropdown,
    setDropdown,
    toggleSearchControls,
    setSearchControls,
    setFocused,
    setHovered,
    setDirectLookup,
    setAutocompleteText,
    hideControls,
    resetSelection,
    openDropdown,
    hideDropdown,
    triggerErrorAnimation,
    triggerModeSwitchAnimation,
    handleModeChange,
    
    // Mode-Specific Actions (delegates)
    // Lookup
    setAIQuery,
    setShowSparkle,
    setAISuggestions,
    addAISuggestion,
    clearAISuggestions,
    
    // Wordlist
    toggleBatchMode,
    setBatchMode,
    addToQueue,
    addBatchToQueue,
    removeFromQueue,
    clearQueue,
    
    // Reset
    reset,
    
    // Expose mode states for advanced usage
    lookupMode,
    wordlistMode,
    currentModeState,
  }
}, {
  persist: {
    key: 'search-bar',
    pick: [
      'searchQuery',
      'showSearchControls',
      // Note: Mode-specific states handle their own persistence
    ]
  }
})
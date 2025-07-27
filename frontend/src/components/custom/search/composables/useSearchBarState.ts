import { ref, computed, watch } from 'vue'
import { useAppStore } from '@/stores'
import type { SearchResult } from '@/types'

export type SearchBarState = 'normal' | 'hovering' | 'focused'
export type SearchMode = 'lookup' | 'wordlist' | 'stage'

interface UseSearchBarStateOptions {
  initialQuery?: string
  hideDelay?: number
  scrollThreshold?: number
}

/**
 * Composable for managing SearchBar state and transitions
 * Handles overall state management, mode transitions, and core state logic
 */
export function useSearchBarState(options: UseSearchBarStateOptions = {}) {
  const store = useAppStore()
  
  // Core state
  const query = ref(options.initialQuery || store.searchQuery || '')
  const currentState = ref<SearchBarState>('normal')
  const isContainerHovered = ref(false)
  const isFocused = ref(false)
  const inputFocused = ref(false)
  const isShrunken = ref(false)
  const isInteractingWithSearchArea = ref(false)
  
  // Search state
  const isSearching = ref(false)
  const searchResults = ref<SearchResult[]>([])
  const selectedIndex = ref(0)
  
  // AI mode state
  const isAIQuery = ref(store.sessionState.isAIQuery || false)
  const showSparkle = ref(store.sessionState.isAIQuery || false)
  const showErrorAnimation = ref(false)
  const aiSuggestions = ref<string[]>([])
  
  // UI state
  const showControls = ref(false)
  const showResults = ref(false)
  const searchBarHeight = ref(64)
  const textareaMinHeight = ref(48)
  const expandButtonVisible = ref(false)
  
  // Modal state
  const showExpandModal = ref(false)
  const expandedQuery = ref('')
  
  // Timers
  let searchTimer: ReturnType<typeof setTimeout> | undefined
  
  // Computed
  const mode = computed(() => store.mode)
  const canToggleMode = computed(() => {
    if (mode.value !== 'suggestions') return true
    return !!store.currentEntry
  })
  
  const placeholder = computed(() =>
    mode.value === 'dictionary'
      ? 'Enter a word to define...'
      : 'Enter a word to find synonyms...'
  )
  
  const shouldShowResults = computed(() => {
    return (
      inputFocused.value &&
      query.value.trim().length > 0 &&
      !store.isSearching &&
      !isAIQuery.value
    )
  })
  
  const shouldTriggerAIMode = (queryText: string) => {
    return queryText.length > 10 || queryText.split(' ').length - 1 > 2
  }
  
  // State transitions
  const transitionToState = (newState: SearchBarState) => {
    if (currentState.value === newState) return
    currentState.value = newState
  }
  
  // State update methods
  const updateSearchAreaInteraction = (interacting: boolean) => {
    isInteractingWithSearchArea.value = interacting
    if (interacting) {
      setTimeout(() => {
        isInteractingWithSearchArea.value = false
      }, 100)
    }
  }
  
  const updateAIMode = (active: boolean, queryText?: string) => {
    isAIQuery.value = active
    showSparkle.value = active
    store.sessionState.isAIQuery = active
    store.sessionState.aiQueryText = active ? (queryText || query.value) : ''
  }
  
  const updateSearchResults = (results: SearchResult[], resetIndex = true) => {
    searchResults.value = results
    if (resetIndex) {
      selectedIndex.value = 0
      store.searchSelectedIndex = 0
    }
    
    if (store.sessionState) {
      store.sessionState.searchResults = results
    }
  }
  
  const clearSearchState = () => {
    searchResults.value = []
    isSearching.value = false
    selectedIndex.value = 0
  }
  
  const showError = (duration = 600) => {
    showErrorAnimation.value = true
    setTimeout(() => {
      showErrorAnimation.value = false
    }, duration)
  }
  
  const updateTextareaHeight = (height: number) => {
    searchBarHeight.value = Math.max(64, height + 32)
  }
  
  // Watchers
  watch(shouldShowResults, (newVal) => {
    showResults.value = newVal
  })
  
  watch(() => store.showControls, (newVal) => {
    showControls.value = newVal
  }, { immediate: true })
  
  watch(query, () => {
    if (isAIQuery.value) {
      store.sessionState.aiQueryText = query.value
    }
    
    // Update expand button visibility
    expandButtonVisible.value = isAIQuery.value || query.value.length > 80 || query.value.includes('\n')
  })
  
  // Cleanup
  const cleanup = () => {
    clearTimeout(searchTimer)
  }
  
  return {
    // State
    query,
    currentState,
    isContainerHovered,
    isFocused,
    inputFocused,
    isShrunken,
    isInteractingWithSearchArea,
    isSearching,
    searchResults,
    selectedIndex,
    isAIQuery,
    showSparkle,
    showErrorAnimation,
    aiSuggestions,
    showControls,
    showResults,
    searchBarHeight,
    textareaMinHeight,
    expandButtonVisible,
    showExpandModal,
    expandedQuery,
    searchTimer,
    
    // Computed
    mode,
    canToggleMode,
    placeholder,
    shouldShowResults,
    
    // Methods
    shouldTriggerAIMode,
    transitionToState,
    updateSearchAreaInteraction,
    updateAIMode,
    updateSearchResults,
    clearSearchState,
    showError,
    updateTextareaHeight,
    cleanup,
  }
}
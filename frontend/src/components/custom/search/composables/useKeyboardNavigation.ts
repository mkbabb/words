import { nextTick, type Ref } from 'vue'
import { useMagicKeys } from '@vueuse/core'
import type { SearchResult } from '@/types'

interface UseKeyboardNavigationOptions {
  searchResults: Ref<SearchResult[]>
  selectedIndex: Ref<number>
  showControls: Ref<boolean>
  showResults: Ref<boolean>
  searchInput: Ref<HTMLTextAreaElement | undefined>
  searchResultsContainer: Ref<HTMLDivElement | undefined>
  resultRefs: (HTMLButtonElement | null)[]
  onSelectResult: (result: SearchResult) => void
  onEnter: () => void
  onEscape: () => void
}

/**
 * Composable for managing keyboard navigation
 * Handles arrow keys, enter, escape, and other keyboard interactions
 */
export function useKeyboardNavigation({
  searchResults,
  selectedIndex,
  showControls,
  showResults,
  searchInput,
  searchResultsContainer,
  resultRefs,
  onSelectResult,
  onEnter,
  onEscape,
}: UseKeyboardNavigationOptions) {
  // Magic keys
  const { escape } = useMagicKeys()
  
  // Global enter handler
  let globalEnterHandler: ((e: KeyboardEvent) => void) | undefined
  
  // Navigation methods
  const navigateResults = (direction: number) => {
    if (searchResults.value.length === 0) return
    
    selectedIndex.value = Math.max(
      0,
      Math.min(
        searchResults.value.length - 1,
        selectedIndex.value + direction
      )
    )
    
    // Scroll selected item into view
    nextTick(() => {
      const selectedElement = resultRefs[selectedIndex.value]
      if (selectedElement && searchResultsContainer.value) {
        selectedElement.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
        })
      }
    })
  }
  
  const handleEnterKey = (event: KeyboardEvent) => {
    event.preventDefault()
    onEnter()
  }
  
  const handleEscapeKey = () => {
    if (showControls.value || showResults.value) {
      onEscape()
    } else {
      // Nothing shown: blur input
      searchInput.value?.blur()
    }
  }
  
  const handleTabKey = (event: KeyboardEvent) => {
    event.preventDefault()
    // Tab key is handled by autocomplete
  }
  
  const handleArrowDown = (event: KeyboardEvent) => {
    event.preventDefault()
    navigateResults(1)
  }
  
  const handleArrowUp = (event: KeyboardEvent) => {
    event.preventDefault()
    navigateResults(-1)
  }
  
  const handleResultClick = (result: SearchResult, index: number) => {
    selectedIndex.value = index
    onSelectResult(result)
  }
  
  const handleResultHover = (index: number) => {
    selectedIndex.value = index
  }
  
  // Setup global enter handler for unfocused search
  const setupGlobalEnterHandler = (isFocused: Ref<boolean>, query: Ref<string>) => {
    globalEnterHandler = (e: KeyboardEvent) => {
      if (e.key === 'Enter' && !isFocused.value && query.value.trim()) {
        e.preventDefault()
        onEnter()
      }
    }
    window.addEventListener('keydown', globalEnterHandler)
  }
  
  // Cleanup global handler
  const cleanupGlobalEnterHandler = () => {
    if (globalEnterHandler) {
      window.removeEventListener('keydown', globalEnterHandler)
      globalEnterHandler = undefined
    }
  }
  
  // Watch escape key
  const watchEscapeKey = () => {
    return escape
  }
  
  return {
    // Methods
    navigateResults,
    handleEnterKey,
    handleEscapeKey,
    handleTabKey,
    handleArrowDown,
    handleArrowUp,
    handleResultClick,
    handleResultHover,
    setupGlobalEnterHandler,
    cleanupGlobalEnterHandler,
    watchEscapeKey,
  }
}
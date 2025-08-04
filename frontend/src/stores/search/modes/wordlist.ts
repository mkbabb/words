import { ref, readonly, shallowRef } from 'vue'
import type { ModeHandler } from '@/stores/types/mode-types'
import type { SearchMode } from '@/types'
import {
  ViewModes,
  WordlistFilterTypes,
  DEFAULT_VIEW_MODE,
  DEFAULT_WORDLIST_FILTERS,
  type ViewMode,
  type WordlistFilters,
  type SortCriterion
} from '@/stores/types/constants'

/**
 * Wordlist mode unified store
 * Contains all wordlist-specific configuration, search bar state, and UI preferences
 */
export function useWordlistMode() {
  // ==========================================================================
  // CONFIGURATION STATE
  // ==========================================================================
  
  const selectedWordlist = ref<string | null>(null)
  
  const wordlistFilters = shallowRef<WordlistFilters>(DEFAULT_WORDLIST_FILTERS)
  
  const wordlistSortCriteria = shallowRef<SortCriterion[]>([])
  
  // ==========================================================================
  // SEARCH BAR STATE
  // ==========================================================================
  
  const batchMode = ref(false)
  const processingQueue = ref<string[]>([])
  
  // ==========================================================================
  // UI STATE (future expansion)
  // ==========================================================================
  
  // Wordlist-specific UI preferences
  const viewMode = ref<ViewMode>(DEFAULT_VIEW_MODE)
  const itemsPerPage = ref(25)
  
  // ==========================================================================
  // CONFIGURATION ACTIONS
  // ==========================================================================
  
  const setWordlist = (wordlistId: string | null) => {
    selectedWordlist.value = wordlistId
  }
  
  const setWordlistFilters = (filters: Partial<typeof wordlistFilters.value>) => {
    wordlistFilters.value = { ...wordlistFilters.value, ...filters }
  }
  
  const toggleWordlistFilter = (filterName: keyof WordlistFilters) => {
    wordlistFilters.value = {
      ...wordlistFilters.value,
      [filterName]: !wordlistFilters.value[filterName]
    }
  }
  
  const setWordlistSortCriteria = (criteria: SortCriterion[]) => {
    wordlistSortCriteria.value = [...criteria]
  }
  
  const addSortCriterion = (criterion: SortCriterion) => {
    wordlistSortCriteria.value = [...wordlistSortCriteria.value, criterion]
  }
  
  const removeSortCriterion = (index: number) => {
    wordlistSortCriteria.value = wordlistSortCriteria.value.filter((_, i) => i !== index)
  }
  
  const clearSortCriteria = () => {
    wordlistSortCriteria.value = []
  }
  
  // ==========================================================================
  // SEARCH BAR ACTIONS
  // ==========================================================================
  
  const toggleBatchMode = () => {
    batchMode.value = !batchMode.value
    if (!batchMode.value) {
      // Clear queue when disabling batch mode
      processingQueue.value = []
    }
  }
  
  const setBatchMode = (enabled: boolean) => {
    batchMode.value = enabled
    if (!enabled) {
      processingQueue.value = []
    }
  }
  
  const addToQueue = (word: string) => {
    if (!processingQueue.value.includes(word)) {
      processingQueue.value = [...processingQueue.value, word]
    }
  }
  
  const addBatchToQueue = (words: string[]) => {
    const uniqueWords = words.filter(word => !processingQueue.value.includes(word))
    processingQueue.value = [...processingQueue.value, ...uniqueWords]
  }
  
  const removeFromQueue = (word: string) => {
    processingQueue.value = processingQueue.value.filter(w => w !== word)
  }
  
  const clearQueue = () => {
    processingQueue.value = []
  }
  
  const getQueueLength = () => processingQueue.value.length
  
  const isInQueue = (word: string) => processingQueue.value.includes(word)
  
  // ==========================================================================
  // UI ACTIONS
  // ==========================================================================
  
  const setViewMode = (mode: ViewMode) => {
    viewMode.value = mode
  }
  
  const toggleViewMode = () => {
    viewMode.value = viewMode.value === ViewModes.LIST ? ViewModes.GRID : ViewModes.LIST
  }
  
  const setItemsPerPage = (count: number) => {
    itemsPerPage.value = count
  }
  
  // ==========================================================================
  // STATE MANAGEMENT
  // ==========================================================================
  
  const getConfig = () => ({
    filters: { ...wordlistFilters.value },
    sortCriteria: [...wordlistSortCriteria.value],
    selectedWordlist: selectedWordlist.value
  })
  
  const setConfig = (config: any) => {
    if (config.filters) setWordlistFilters(config.filters)
    if (config.sortCriteria) setWordlistSortCriteria(config.sortCriteria)
    if (config.selectedWordlist !== undefined) setWordlist(config.selectedWordlist)
  }
  
  const getSearchBarState = () => ({
    batchMode: batchMode.value,
    processingQueue: [...processingQueue.value]
  })
  
  const setSearchBarState = (state: any) => {
    if (state.batchMode !== undefined) setBatchMode(state.batchMode)
    if (state.processingQueue) processingQueue.value = [...state.processingQueue]
  }
  
  const getUIState = () => ({
    viewMode: viewMode.value,
    itemsPerPage: itemsPerPage.value
  })
  
  const setUIState = (state: any) => {
    if (state.viewMode) setViewMode(state.viewMode)
    if (state.itemsPerPage !== undefined) setItemsPerPage(state.itemsPerPage)
  }
  
  const reset = () => {
    // Reset config
    selectedWordlist.value = null
    wordlistFilters.value = DEFAULT_WORDLIST_FILTERS
    wordlistSortCriteria.value = []
    
    // Reset search bar
    batchMode.value = false
    processingQueue.value = []
    
    // Reset UI
    viewMode.value = DEFAULT_VIEW_MODE
    itemsPerPage.value = 25
  }
  
  // ==========================================================================
  // MODE HANDLER
  // ==========================================================================
  
  const handler: ModeHandler = {
    onEnter: async (previousMode: SearchMode) => {
      console.log('📚 Entering wordlist mode from:', previousMode)
    },
    
    onExit: async (nextMode: SearchMode) => {
      console.log('👋 Exiting wordlist mode to:', nextMode)
      // Disable batch mode when leaving
      setBatchMode(false)
    },
    
    validateConfig: (config: any) => {
      return true // Wordlist config is always valid
    },
    
    getDefaultConfig: () => ({
      filters: DEFAULT_WORDLIST_FILTERS,
      sortCriteria: [],
      selectedWordlist: null
    })
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // Configuration State
    selectedWordlist: readonly(selectedWordlist),
    wordlistFilters: readonly(wordlistFilters),
    wordlistSortCriteria: readonly(wordlistSortCriteria),
    
    // Search Bar State
    batchMode: readonly(batchMode),
    processingQueue: readonly(processingQueue),
    
    // UI State
    viewMode: readonly(viewMode),
    itemsPerPage: readonly(itemsPerPage),
    
    // Configuration Actions
    setWordlist,
    setWordlistFilters,
    toggleWordlistFilter,
    setWordlistSortCriteria,
    addSortCriterion,
    removeSortCriterion,
    clearSortCriteria,
    
    // Search Bar Actions
    toggleBatchMode,
    setBatchMode,
    addToQueue,
    addBatchToQueue,
    removeFromQueue,
    clearQueue,
    getQueueLength,
    isInQueue,
    
    // UI Actions
    setViewMode,
    toggleViewMode,
    setItemsPerPage,
    
    // State Management
    getConfig,
    setConfig,
    getSearchBarState,
    setSearchBarState,
    getUIState,
    setUIState,
    reset,
    
    // Mode Handler
    handler
  }
}
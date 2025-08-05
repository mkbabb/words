import { defineStore } from 'pinia'
import { ref, readonly, computed, shallowRef } from 'vue'
import { wordlistsApi } from '@/api'
import type { ModeHandler } from '@/stores/types/mode-types'
import type { SearchMode, WordListItem } from '@/types'
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
 * Unified wordlist mode store
 * Combines configuration, search bar state, UI preferences, and search results
 */
export const useWordlistMode = defineStore('wordlistMode', () => {
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
  // UI STATE
  // ==========================================================================
  
  const viewMode = ref<ViewMode>(DEFAULT_VIEW_MODE)
  const itemsPerPage = ref(25)
  
  // ==========================================================================
  // RESULTS STATE
  // ==========================================================================
  
  const results = shallowRef<WordListItem[]>([])
  
  const pagination = ref({
    offset: 0,
    limit: 100,
    total: 0,
    hasMore: false
  })
  
  const currentWordlistId = ref<string | null>(null)
  const currentQuery = ref<string>('')
  
  const filters = ref({
    mastery: [] as ('bronze' | 'silver' | 'gold')[],
    temperature: [] as ('hot' | 'due')[],
    partOfSpeech: [] as string[],
    minScore: 0.4,
  })
  
  const batchProcessing = ref({
    isProcessing: false,
    processed: 0,
    total: 0,
    currentWord: '',
    errors: [] as string[]
  })
  
  let abortController: AbortController | null = null
  
  // ==========================================================================
  // COMPUTED
  // ==========================================================================
  
  const state = computed(() => ({
    hasResults: results.value.length > 0,
    resultCount: results.value.length,
    isSearchActive: abortController !== null,
    isEmpty: results.value.length === 0,
    canLoadMore: pagination.value.hasMore,
    isProcessingBatch: batchProcessing.value.isProcessing,
    processingProgress: batchProcessing.value.total > 0 
      ? batchProcessing.value.processed / batchProcessing.value.total 
      : 0,
  }))
  
  const filteredResults = computed(() => {
    let filtered = results.value
    
    // Apply mastery filter
    if (filters.value.mastery.length > 0) {
      filtered = filtered.filter(item => 
        filters.value.mastery.includes(item.mastery_level as any)
      )
    }
    
    // Apply temperature filter
    if (filters.value.temperature.length > 0) {
      filtered = filtered.filter(item => 
        filters.value.temperature.includes(item.temperature as any)
      )
    }
    
    // Apply part of speech filter
    // Note: WordListItem doesn't have part_of_speech property
    // This filter is currently disabled as it requires loading definition data
    // if (filters.value.partOfSpeech.length > 0) {
    //   filtered = filtered.filter(item => 
    //     filters.value.partOfSpeech.some(pos => 
    //       item.part_of_speech?.includes(pos)
    //     )
    //   )
    // }
    
    return filtered
  })
  
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
  // RESULTS OPERATIONS
  // ==========================================================================
  
  const setResults = (newResults: WordListItem[], replace = true) => {
    if (replace) {
      results.value = [...newResults]
    } else {
      results.value = [...results.value, ...newResults]
    }
  }
  
  const clearResults = () => {
    results.value = []
    pagination.value = { offset: 0, limit: 100, total: 0, hasMore: false }
    currentQuery.value = ''
    resetBatchProcessing()
  }
  
  const getWordlistWords = async (wordlistId: string, offset = 0, limit = 100) => {
    currentWordlistId.value = wordlistId
    
    // Cancel any existing search
    cancelSearch()
    abortController = new AbortController()
    
    try {
      const response = await wordlistsApi.getWordlistWords(wordlistId, {
        offset,
        limit
      })
      
      const items = response.items || []
      const replace = offset === 0
      
      // Update pagination
      pagination.value = {
        offset: offset + items.length,
        limit,
        total: response.total || items.length,
        hasMore: (response.total || 0) > offset + items.length
      }
      
      setResults(items, replace)
      return items
      
    } catch (error: any) {
      if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
        console.log('[WordlistMode] Request cancelled')
        return []
      }
      
      console.error('[WordlistMode] Failed to get wordlist words:', error)
      clearResults()
      throw error
    } finally {
      abortController = null
    }
  }
  
  const searchWordlist = async (wordlistId: string, query: string, offset = 0, limit = 50) => {
    currentWordlistId.value = wordlistId
    currentQuery.value = query
    
    // Cancel any existing search
    cancelSearch()
    abortController = new AbortController()
    
    try {
      const response = await wordlistsApi.searchWordlist(wordlistId, {
        query,
        max_results: limit,
        min_score: filters.value.minScore,
        offset,
        limit
      })
      
      const items = response.items || []
      const replace = offset === 0
      
      // Update pagination
      pagination.value = {
        offset: offset + items.length,
        limit,
        total: response.total || items.length,
        hasMore: (response.total || 0) > offset + items.length
      }
      
      setResults(items, replace)
      return items
      
    } catch (error: any) {
      if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
        console.log('[WordlistMode] Search cancelled')
        return []
      }
      
      console.error('[WordlistMode] Failed to search wordlist:', error)
      clearResults()
      throw error
    } finally {
      abortController = null
    }
  }
  
  const loadMore = async () => {
    if (!pagination.value.hasMore || !currentWordlistId.value) return []
    
    if (currentQuery.value) {
      return await searchWordlist(
        currentWordlistId.value, 
        currentQuery.value, 
        pagination.value.offset,
        pagination.value.limit
      )
    } else {
      return await getWordlistWords(
        currentWordlistId.value,
        pagination.value.offset,
        pagination.value.limit
      )
    }
  }
  
  const cancelSearch = () => {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
  }
  
  // ==========================================================================
  // FILTERING OPERATIONS
  // ==========================================================================
  
  const setFilters = (newFilters: Partial<typeof filters.value>) => {
    filters.value = { ...filters.value, ...newFilters }
  }
  
  const resetFilters = () => {
    filters.value = {
      mastery: [],
      temperature: [],
      partOfSpeech: [],
      minScore: 0.4,
    }
  }
  
  // ==========================================================================
  // BATCH PROCESSING
  // ==========================================================================
  
  const startBatchProcessing = (total: number) => {
    batchProcessing.value = {
      isProcessing: true,
      processed: 0,
      total,
      currentWord: '',
      errors: []
    }
  }
  
  const updateBatchProgress = (processed: number, currentWord: string, error?: string) => {
    batchProcessing.value.processed = processed
    batchProcessing.value.currentWord = currentWord
    
    if (error) {
      batchProcessing.value.errors.push(error)
    }
  }
  
  const completeBatchProcessing = () => {
    batchProcessing.value.isProcessing = false
  }
  
  const resetBatchProcessing = () => {
    batchProcessing.value = {
      isProcessing: false,
      processed: 0,
      total: 0,
      currentWord: '',
      errors: []
    }
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
    
    // Reset results
    clearResults()
    resetFilters()
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
    
    // Results State
    results: readonly(results),
    pagination: readonly(pagination),
    currentWordlistId: readonly(currentWordlistId),
    currentQuery: readonly(currentQuery),
    filters: filters, // Mutable for persistence
    batchProcessing: readonly(batchProcessing),
    
    // Computed
    state,
    filteredResults,
    
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
    
    // Results Operations
    setResults,
    clearResults,
    getWordlistWords,
    searchWordlist,
    loadMore,
    cancelSearch,
    
    // Filtering
    setFilters,
    resetFilters,
    
    // Batch Processing
    startBatchProcessing,
    updateBatchProgress,
    completeBatchProcessing,
    resetBatchProcessing,
    
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
}, {
  persist: {
    key: 'wordlist-mode',
    pick: ['selectedWordlist', 'wordlistFilters', 'wordlistSortCriteria', 'viewMode', 'itemsPerPage', 'filters']
  }
})
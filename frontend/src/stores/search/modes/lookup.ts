import { defineStore } from 'pinia'
import { ref, readonly, computed, shallowRef } from 'vue'
import { dictionaryApi } from '@/api'
import { normalizeWord } from '@/utils'
import { CARD_VARIANTS } from '@/types'
import type { ModeHandler } from '@/stores/types/mode-types'
import type { SearchMode, SearchResult, CardVariant } from '@/types'
import { 
  PronunciationModes, 
  DEFAULT_CARD_VARIANT, 
  DEFAULT_PRONUNCIATION_MODE,
  DEFAULT_SOURCES,
  DEFAULT_LANGUAGES,
  type PronunciationMode,
  type DictionarySource,
  type Language
} from '@/stores/types/constants'

/**
 * Unified lookup mode store
 * Combines configuration, search bar state, UI preferences, and search results
 */
export const useLookupMode = defineStore('lookupMode', () => {
  // ==========================================================================
  // CONFIGURATION STATE
  // ==========================================================================
  
  const selectedSources = ref<DictionarySource[]>(DEFAULT_SOURCES)
  const selectedLanguages = ref<Language[]>(DEFAULT_LANGUAGES)
  const noAI = ref(true)
  const enableSemantic = ref(false)
  const semanticWeight = ref(0.7)
  
  // ==========================================================================
  // SEARCH BAR STATE
  // ==========================================================================
  
  const isAIQuery = ref(false)
  const showSparkle = ref(false)
  const aiSuggestions = ref<string[]>([])
  
  // ==========================================================================
  // UI STATE
  // ==========================================================================
  
  const selectedCardVariant = ref<CardVariant>(DEFAULT_CARD_VARIANT)
  const pronunciationMode = ref<PronunciationMode>(DEFAULT_PRONUNCIATION_MODE)
  
  // ==========================================================================
  // RESULTS STATE
  // ==========================================================================
  
  const results = shallowRef<SearchResult[]>([])
  const cursorPosition = ref(0)
  const searchMethod = ref<'exact' | 'fuzzy' | 'semantic' | 'ai' | null>(null)
  let abortController: AbortController | null = null
  
  // ==========================================================================
  // COMPUTED
  // ==========================================================================
  
  const state = computed(() => ({
    hasResults: results.value.length > 0,
    resultCount: results.value.length,
    currentMethod: searchMethod.value,
    isSearchActive: abortController !== null,
    isEmpty: results.value.length === 0,
  }))
  
  // ==========================================================================
  // CONFIGURATION ACTIONS
  // ==========================================================================
  
  const toggleSource = (source: DictionarySource) => {
    const sources = selectedSources.value
    if (sources.includes(source)) {
      selectedSources.value = sources.filter((s) => s !== source)
    } else {
      selectedSources.value = [...sources, source]
    }
  }
  
  const setSources = (sources: DictionarySource[]) => {
    selectedSources.value = [...sources]
  }
  
  const toggleLanguage = (language: Language) => {
    const languages = selectedLanguages.value
    if (languages.includes(language)) {
      selectedLanguages.value = languages.filter((l) => l !== language)
    } else {
      selectedLanguages.value = [...languages, language]
    }
  }
  
  const setLanguages = (languages: Language[]) => {
    selectedLanguages.value = [...languages]
  }
  
  const toggleAI = () => {
    noAI.value = !noAI.value
  }
  
  const setAI = (enabled: boolean) => {
    noAI.value = !enabled
  }
  
  const toggleSemantic = () => {
    enableSemantic.value = !enableSemantic.value
  }
  
  const setSemantic = (enabled: boolean) => {
    enableSemantic.value = enabled
  }
  
  const setSemanticWeight = (weight: number) => {
    semanticWeight.value = Math.min(1, Math.max(0, weight))
  }
  
  // ==========================================================================
  // SEARCH BAR ACTIONS
  // ==========================================================================
  
  const setAIQuery = (isAI: boolean) => {
    isAIQuery.value = isAI
    if (isAI) {
      showSparkle.value = true
      // Auto-hide sparkle after animation
      setTimeout(() => {
        showSparkle.value = false
      }, 2000)
    }
  }
  
  const setShowSparkle = (show: boolean) => {
    showSparkle.value = show
  }
  
  const setAISuggestions = (suggestions: string[]) => {
    aiSuggestions.value = [...suggestions]
  }
  
  const addAISuggestion = (suggestion: string) => {
    if (!aiSuggestions.value.includes(suggestion)) {
      aiSuggestions.value = [...aiSuggestions.value, suggestion]
    }
  }
  
  const clearAISuggestions = () => {
    aiSuggestions.value = []
  }
  
  // ==========================================================================
  // UI ACTIONS
  // ==========================================================================
  
  const setCardVariant = (variant: CardVariant) => {
    selectedCardVariant.value = variant
  }
  
  const cycleCardVariant = () => {
    const variants = CARD_VARIANTS as unknown as CardVariant[]
    const currentIndex = variants.indexOf(selectedCardVariant.value)
    const nextIndex = (currentIndex + 1) % variants.length
    selectedCardVariant.value = variants[nextIndex]
  }
  
  const togglePronunciation = () => {
    pronunciationMode.value = pronunciationMode.value === PronunciationModes.PHONETIC 
      ? PronunciationModes.IPA 
      : PronunciationModes.PHONETIC
  }
  
  const setPronunciationMode = (mode: PronunciationMode) => {
    pronunciationMode.value = mode
  }
  
  // ==========================================================================
  // RESULTS OPERATIONS
  // ==========================================================================
  
  const setResults = (newResults: SearchResult[], method?: typeof searchMethod.value) => {
    results.value = [...newResults]
    if (method) {
      searchMethod.value = method
    }
  }
  
  const clearResults = () => {
    results.value = []
    searchMethod.value = null
    cursorPosition.value = 0
  }
  
  const addResults = (newResults: SearchResult[]) => {
    results.value = [...results.value, ...newResults]
  }
  
  const search = async (query: string): Promise<SearchResult[]> => {
    const normalizedQuery = normalizeWord(query)
    
    // Cancel any existing search
    cancelSearch()
    
    // Create new abort controller
    abortController = new AbortController()
    
    try {
      console.log(`[LookupMode] Searching for: ${query}`)
      
      const searchResults = await dictionaryApi.searchWord(normalizedQuery, {
        signal: abortController.signal,
        semantic: enableSemantic.value,
        semantic_weight: semanticWeight.value
      })
      
      // Store results with method detection
      const method = detectSearchMethod(searchResults, normalizedQuery)
      setResults(searchResults, method)
      
      console.log(`[LookupMode] Found ${searchResults.length} results using ${method} method`)
      return searchResults
      
    } catch (error: any) {
      if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
        console.log('[LookupMode] Search cancelled')
        return []
      }
      
      console.error('[LookupMode] Search error:', error)
      clearResults()
      throw error
    } finally {
      abortController = null
    }
  }
  
  const cancelSearch = () => {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
  }
  
  const setCursorPosition = (position: number) => {
    cursorPosition.value = position
  }
  
  const getResultAt = (index: number): SearchResult | null => {
    return results.value[index] || null
  }
  
  const findResultByWord = (word: string): SearchResult | null => {
    return results.value.find(result => result.word.toLowerCase() === word.toLowerCase()) || null
  }
  
  // ==========================================================================
  // UTILITIES
  // ==========================================================================
  
  const detectSearchMethod = (results: SearchResult[], query: string): typeof searchMethod.value => {
    if (results.length === 0) return null
    
    const normalizedQuery = query.toLowerCase()
    const exactMatch = results.find(result => result.word.toLowerCase() === normalizedQuery)
    
    if (exactMatch) return 'exact'
    
    // Check if results are fuzzy matches (similar words)
    const hasFuzzyMatches = results.some(result => 
      result.word.toLowerCase().includes(normalizedQuery) || 
      normalizedQuery.includes(result.word.toLowerCase())
    )
    
    if (hasFuzzyMatches) return 'fuzzy'
    
    // If no exact or fuzzy matches, assume semantic/AI
    return 'semantic'
  }
  
  // ==========================================================================
  // STATE MANAGEMENT
  // ==========================================================================
  
  const getConfig = () => ({
    selectedSources: selectedSources.value,
    selectedLanguages: selectedLanguages.value,
    noAI: noAI.value,
    enableSemantic: enableSemantic.value,
    semanticWeight: semanticWeight.value
  })
  
  const setConfig = (config: any) => {
    if (config.selectedSources) setSources(config.selectedSources)
    if (config.selectedLanguages) setLanguages(config.selectedLanguages)
    if (config.noAI !== undefined) noAI.value = config.noAI
    if (config.enableSemantic !== undefined) enableSemantic.value = config.enableSemantic
    if (config.semanticWeight !== undefined) semanticWeight.value = config.semanticWeight
  }
  
  const getSearchBarState = () => ({
    isAIQuery: isAIQuery.value,
    showSparkle: showSparkle.value,
    aiSuggestions: [...aiSuggestions.value]
  })
  
  const setSearchBarState = (state: any) => {
    if (state.isAIQuery !== undefined) setAIQuery(state.isAIQuery)
    if (state.showSparkle !== undefined) setShowSparkle(state.showSparkle)
    if (state.aiSuggestions) setAISuggestions(state.aiSuggestions)
  }
  
  const getUIState = () => ({
    selectedCardVariant: selectedCardVariant.value,
    pronunciationMode: pronunciationMode.value
  })
  
  const setUIState = (state: any) => {
    if (state.selectedCardVariant) setCardVariant(state.selectedCardVariant)
    if (state.pronunciationMode) setPronunciationMode(state.pronunciationMode)
  }
  
  const reset = () => {
    // Reset config
    selectedSources.value = DEFAULT_SOURCES
    selectedLanguages.value = DEFAULT_LANGUAGES
    noAI.value = true
    
    // Reset search bar
    isAIQuery.value = false
    showSparkle.value = false
    aiSuggestions.value = []
    
    // Reset UI
    selectedCardVariant.value = DEFAULT_CARD_VARIANT
    pronunciationMode.value = DEFAULT_PRONUNCIATION_MODE
    
    // Reset results
    clearResults()
  }
  
  // ==========================================================================
  // MODE HANDLER
  // ==========================================================================
  
  const handler: ModeHandler = {
    onEnter: async (previousMode: SearchMode) => {
      console.log('🔍 Entering lookup mode from:', previousMode)
      // Clear AI state when entering
      isAIQuery.value = false
      showSparkle.value = false
      clearAISuggestions()
    },
    
    onExit: async (nextMode: SearchMode) => {
      console.log('👋 Exiting lookup mode to:', nextMode)
      // Clear AI suggestions when leaving
      clearAISuggestions()
    },
    
    validateConfig: (config: any) => {
      return config.selectedSources?.length > 0 && config.selectedLanguages?.length > 0
    },
    
    getDefaultConfig: () => ({
      selectedSources: DEFAULT_SOURCES,
      selectedLanguages: DEFAULT_LANGUAGES,
      noAI: true
    })
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // Configuration State
    selectedSources: readonly(selectedSources),
    selectedLanguages: readonly(selectedLanguages),
    noAI: readonly(noAI),
    enableSemantic: readonly(enableSemantic),
    semanticWeight: readonly(semanticWeight),
    
    // Search Bar State
    isAIQuery: readonly(isAIQuery),
    showSparkle: readonly(showSparkle),
    aiSuggestions: readonly(aiSuggestions),
    
    // UI State
    selectedCardVariant: readonly(selectedCardVariant),
    pronunciationMode: readonly(pronunciationMode),
    
    // Results State
    results: readonly(results),
    cursorPosition: readonly(cursorPosition),
    searchMethod: readonly(searchMethod),
    
    // Computed
    state,
    
    // Configuration Actions
    toggleSource,
    setSources,
    toggleLanguage,
    setLanguages,
    toggleAI,
    setAI,
    toggleSemantic,
    setSemantic,
    setSemanticWeight,
    
    // Search Bar Actions
    setAIQuery,
    setShowSparkle,
    setAISuggestions,
    addAISuggestion,
    clearAISuggestions,
    
    // UI Actions
    setCardVariant,
    cycleCardVariant,
    togglePronunciation,
    setPronunciationMode,
    
    // Results Operations
    setResults,
    clearResults,
    addResults,
    search,
    cancelSearch,
    setCursorPosition,
    getResultAt,
    findResultByWord,
    
    // State Management
    getConfig,
    setConfig,
    getSearchBarState,
    setSearchBarState,
    getUIState,
    setUIState,
    reset,
    
    // Utilities
    detectSearchMethod,
    
    // Mode Handler
    handler
  }
}, {
  persist: {
    key: 'lookup-mode',
    pick: ['selectedSources', 'selectedLanguages', 'noAI', 'enableSemantic', 'semanticWeight', 'selectedCardVariant', 'pronunciationMode', 'cursorPosition']
  }
})
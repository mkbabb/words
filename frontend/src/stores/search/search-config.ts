import { defineStore } from 'pinia'
import { ref, readonly, computed } from 'vue'
import type { SearchMode, SearchSubMode, SearchSubModeMap } from '@/types'
import type { DictionarySource, Language } from '@/stores/types/constants'
import { useLookupMode } from './modes/lookup'
import { useWordlistMode } from './modes/wordlist'
import { useWordOfTheDayModeConfig } from './modes/word-of-the-day'
import { useStageModeConfig } from './modes/stage'

/**
 * Refactored SearchConfigStore with mode-specific encapsulation
 * Central orchestrator for all search modes and their configurations
 */
export const useSearchConfigStore = defineStore('searchConfig', () => {
  // ==========================================================================
  // CORE MODE STATE
  // ==========================================================================
  
  const searchMode = ref<SearchMode>('lookup')
  const previousMode = ref<SearchMode>('lookup')
  
  const searchSubMode = ref<Record<SearchMode, SearchSubMode<SearchMode>>>({
    lookup: 'dictionary',
    wordlist: 'all',
    'word-of-the-day': 'current',
    stage: 'test'
  })
  
  // Query persistence across modes
  const savedQueries = ref<Record<SearchMode, string>>({
    'lookup': '',
    'wordlist': '',
    'word-of-the-day': '',
    'stage': ''
  })
  
  const showControls = ref(false)
  
  // ==========================================================================
  // MODE-SPECIFIC CONFIGURATIONS
  // ==========================================================================
  
  const lookupMode = useLookupMode()
  const wordlistMode = useWordlistMode()
  const wordOfTheDayConfig = useWordOfTheDayModeConfig()
  const stageConfig = useStageModeConfig()
  
  // Mode configuration registry
  const modeConfigs = {
    lookup: lookupMode,
    wordlist: wordlistMode,
    'word-of-the-day': wordOfTheDayConfig,
    stage: stageConfig
  }
  
  // ==========================================================================
  // COMPUTED PROPERTIES
  // ==========================================================================
  
  // Get current mode configuration
  const currentModeConfig = computed(() => {
    return modeConfigs[searchMode.value]
  })
  
  // Legacy compatibility
  const lookupSubMode = computed(() => searchSubMode.value.lookup)
  
  // Expose mode-specific configs as computed properties for convenience
  const selectedSources = computed(() => lookupMode.selectedSources.value)
  const selectedLanguages = computed(() => lookupMode.selectedLanguages.value)
  const noAI = computed(() => lookupMode.noAI.value)
  const selectedWordlist = computed(() => wordlistMode.selectedWordlist.value)
  const wordlistFilters = computed(() => wordlistMode.wordlistFilters.value)
  const wordlistSortCriteria = computed(() => wordlistMode.wordlistSortCriteria.value)
  
  // ==========================================================================
  // MODE MANAGEMENT
  // ==========================================================================
  
  const setMode = async (newMode: SearchMode, currentQuery?: string) => {
    if (newMode !== searchMode.value) {
      console.log('🔄 Mode change:', searchMode.value, '->', newMode)
      
      // Save current query if provided
      if (currentQuery !== undefined) {
        saveCurrentQuery(currentQuery)
      }
      
      // Execute exit handler for current mode
      const currentConfig = modeConfigs[searchMode.value]
      if (currentConfig.handler?.onExit) {
        await currentConfig.handler.onExit(newMode)
      }
      
      // Update mode
      previousMode.value = searchMode.value
      searchMode.value = newMode
      
      // Execute enter handler for new mode
      const newConfig = modeConfigs[newMode]
      if (newConfig.handler?.onEnter) {
        await newConfig.handler.onEnter(previousMode.value)
      }
      
      console.log('✅ Mode changed to:', newMode)
      
      // Return saved query for the new mode
      return getSavedQuery(newMode)
    }
    return ''
  }
  
  const setSubMode = <T extends SearchMode>(mode: T, newSubMode: SearchSubModeMap[T]) => {
    const currentSubMode = searchSubMode.value[mode]
    if (newSubMode !== currentSubMode) {
      console.log(`🔄 ${mode} sub-mode change:`, currentSubMode, '->', newSubMode)
      
      // Cancel any in-progress requests when switching modes
      try {
        const { useSearchResultsStore } = require('./search-results')
        const searchResultsStore = useSearchResultsStore()
        searchResultsStore.cancelSearch()
      } catch (e) {
        console.warn('Could not cancel in-progress requests:', e)
      }
      
      searchSubMode.value = {
        ...searchSubMode.value,
        [mode]: newSubMode
      }
      console.log(`✅ ${mode} sub-mode changed to:`, newSubMode)
    }
  }
  
  const getSubMode = <T extends SearchMode>(mode: T): SearchSubModeMap[T] => {
    return searchSubMode.value[mode] as SearchSubModeMap[T]
  }
  
  const toggleSearchMode = () => {
    const modes: SearchMode[] = ['lookup', 'wordlist', 'word-of-the-day', 'stage']
    const currentIndex = modes.indexOf(searchMode.value)
    const nextIndex = (currentIndex + 1) % modes.length
    setMode(modes[nextIndex])
  }
  
  // ==========================================================================
  // QUERY MANAGEMENT
  // ==========================================================================
  
  const saveCurrentQuery = (query: string) => {
    savedQueries.value[searchMode.value] = query
    console.log('💾 Saved query for', searchMode.value, ':', query)
  }
  
  const getSavedQuery = (mode: SearchMode) => {
    return savedQueries.value[mode] || ''
  }
  
  const getPreviousMode = () => previousMode.value
  
  // ==========================================================================
  // MODE-SPECIFIC ACTION DELEGATES
  // ==========================================================================
  
  // Lookup mode actions
  const toggleSource = (source: DictionarySource) => lookupMode.toggleSource(source)
  const setSources = (sources: DictionarySource[]) => lookupMode.setSources(sources)
  const toggleLanguage = (language: Language) => lookupMode.toggleLanguage(language)
  const setLanguages = (languages: Language[]) => lookupMode.setLanguages(languages)
  const toggleAI = () => lookupMode.toggleAI()
  const setAI = (enabled: boolean) => lookupMode.setAI(enabled)
  
  // Wordlist mode actions
  const setWordlist = (wordlistId: string | null) => wordlistMode.setWordlist(wordlistId)
  const setWordlistFilters = (filters: any) => wordlistMode.setWordlistFilters(filters)
  const toggleWordlistFilter = (filterName: any) => wordlistMode.toggleWordlistFilter(filterName)
  const setWordlistSortCriteria = (criteria: any[]) => wordlistMode.setWordlistSortCriteria(criteria)
  const addSortCriterion = (criterion: any) => wordlistMode.addSortCriterion(criterion)
  const removeSortCriterion = (index: number) => wordlistMode.removeSortCriterion(index)
  const clearSortCriteria = () => wordlistMode.clearSortCriteria()

  // Legacy compatibility methods
  const setLookupMode = (mode: any) => {
    setSubMode('lookup', mode)
  }
  
  // ==========================================================================
  // CONTROL MANAGEMENT
  // ==========================================================================
  
  const toggleControls = () => {
    showControls.value = !showControls.value
  }
  
  const setShowControls = (show: boolean) => {
    showControls.value = show
  }
  
  // ==========================================================================
  // RESET CONFIGURATION
  // ==========================================================================
  
  const resetConfig = () => {
    // Reset core state
    searchMode.value = 'lookup'
    searchSubMode.value = {
      lookup: 'dictionary',
      wordlist: 'all',
      'word-of-the-day': 'current',
      stage: 'test'
    }
    showControls.value = false
    
    // Reset all mode configurations
    lookupMode.reset()
    wordlistMode.reset()
    wordOfTheDayConfig.reset()
    stageConfig.reset()
    
    // Clear saved queries
    savedQueries.value = {
      'lookup': '',
      'wordlist': '',
      'word-of-the-day': '',
      'stage': ''
    }
  }
  
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // Core Mode State
    searchMode: readonly(searchMode),
    searchSubMode: readonly(searchSubMode),
    lookupSubMode: readonly(lookupSubMode),
    previousMode: readonly(previousMode),
    savedQueries: readonly(savedQueries),
    showControls: readonly(showControls),
    
    // Mode-Specific Configurations (read-only exposure)
    lookupConfig: {
      selectedSources,
      selectedLanguages,
      noAI,
      // Actions
      toggleSource,
      setSources,
      toggleLanguage,
      setLanguages,
      toggleAI,
      setAI,
    },
    
    wordlistConfig: {
      selectedWordlist,
      wordlistFilters,
      wordlistSortCriteria,
      // Actions
      setWordlist,
      setWordlistFilters,
      toggleWordlistFilter,
      setWordlistSortCriteria,
      addSortCriterion,
      removeSortCriterion,
      clearSortCriteria,
    },
    
    wordOfTheDayConfig: {
      currentDate: wordOfTheDayConfig.currentDate,
      archiveView: wordOfTheDayConfig.archiveView,
      // Actions
      setCurrentDate: wordOfTheDayConfig.setCurrentDate,
      setToday: wordOfTheDayConfig.setToday,
      toggleArchiveView: wordOfTheDayConfig.toggleArchiveView,
      setArchiveView: wordOfTheDayConfig.setArchiveView,
    },
    
    stageConfig: {
      debugLevel: stageConfig.debugLevel,
      testMode: stageConfig.testMode,
      // Actions
      setDebugLevel: stageConfig.setDebugLevel,
      toggleTestMode: stageConfig.toggleTestMode,
      setTestMode: stageConfig.setTestMode,
    },
    
    // Computed convenience properties (for backward compatibility)
    selectedSources,
    selectedLanguages,
    noAI,
    selectedWordlist,
    wordlistFilters,
    wordlistSortCriteria,
    
    // Mode Management Actions
    setMode,
    setSubMode,
    getSubMode,
    toggleSearchMode,
    getPreviousMode,
    saveCurrentQuery,
    getSavedQuery,
    
    // Control Actions
    toggleControls,
    setShowControls,
    
    // Reset
    resetConfig,
    
    // Action delegates
    toggleSource,
    setSources,
    toggleLanguage,
    setLanguages,
    toggleAI,
    setAI,
    setWordlist,
    setWordlistFilters,
    toggleWordlistFilter,
    setWordlistSortCriteria,
    addSortCriterion,
    removeSortCriterion,
    clearSortCriteria,
    setLookupMode,
    
    // Expose current mode config for advanced usage
    currentModeConfig,
  }
}, {
  persist: {
    key: 'search-config',
    pick: [
      'searchMode',
      'searchSubMode',
      'previousMode',
      'savedQueries',
      'showControls',
      // Note: Mode-specific configs have their own persistence
    ]
  }
})
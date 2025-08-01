import { defineStore } from 'pinia'
import { ref, readonly, nextTick } from 'vue'
import { useRouterSync } from '../composables/useRouterSync'
import { wordlistApi } from '@/api'
import type { 
  SearchMode, 
  ModeOperationOptions, 
  ModeTransitionResult,
  LookupModeConfig,
  WordlistModeConfig,
  WordOfTheDayModeConfig,
  StageModeConfig,
  DEFAULT_MODE_CONFIGS
} from '@/types'

/**
 * SearchConfigStore - Search configuration and mode management
 * Handles search mode, dictionary sources, languages, wordlist selection, and AI settings
 * Uses modern Pinia persistence for automatic state saving
 */
export const useSearchConfigStore = defineStore('searchConfig', () => {
  // ==========================================================================
  // PERSISTED CONFIGURATION STATE
  // ==========================================================================
  
  // Search mode configuration
  const searchMode = ref<SearchMode>('lookup')
  const selectedSources = ref<string[]>(['wiktionary'])
  const selectedLanguages = ref<string[]>(['en'])
  const selectedWordlist = ref<string | null>(null)
  const noAI = ref(true)
  const showControls = ref(false)

  // ==========================================================================
  // ROUTER INTEGRATION
  // ==========================================================================
  
  const { 
    navigateToLookupMode, 
    navigateToWordlist, 
    navigateToHome,
    navigateToWordOfTheDay,
    navigateToStage,
    updateRouterForCurrentEntry 
  } = useRouterSync()

  // ==========================================================================
  // INTERNAL HELPERS
  // ==========================================================================

  /**
   * Type-safe mode navigation handler
   * Eliminates the need for mode-specific parameter passing
   */
  const handleModeNavigation = async <T extends SearchMode>(
    mode: T, 
    config: any // Will be properly typed based on mode
  ) => {
    switch (mode) {
      case 'lookup': {
        const lookupConfig = config as LookupModeConfig
        if (lookupConfig.query?.trim()) {
          console.log('🧭 Navigating to lookup with query:', lookupConfig.query)
          navigateToLookupMode(lookupConfig.query, lookupConfig.displayMode || 'dictionary')
        } else if (lookupConfig.currentEntry?.word) {
          console.log('🧭 Updating router for existing lookup:', lookupConfig.currentEntry.word)
          updateRouterForCurrentEntry(
            lookupConfig.currentEntry, 
            lookupConfig.displayMode || 'dictionary', 
            'lookup'
          )
        } else {
          console.log('🧭 No query or entry, going to home')
          navigateToHome()
        }
        break
      }
      
      case 'wordlist': {
        const wordlistConfig = config as WordlistModeConfig
        const targetWordlistId = wordlistConfig.wordlistId || selectedWordlist.value
        
        if (targetWordlistId) {
          console.log('🧭 Navigating to wordlist:', targetWordlistId, 'with config')
          
          // Build filters object from config
          const filters = wordlistConfig.filters ? {
            ...wordlistConfig.filters,
            ...(wordlistConfig.chunking && { chunking: wordlistConfig.chunking }),
            ...(wordlistConfig.sortCriteria && { sortCriteria: wordlistConfig.sortCriteria })
          } : undefined
          
          navigateToWordlist(targetWordlistId, filters, wordlistConfig.query)
        } else {
          // Auto-fetch first available wordlist
          console.log('🧭 No wordlist selected, fetching first available')
          try {
            const response = await wordlistApi.getWordlists({ limit: 1 })
            if (response.items?.length > 0) {
              const firstWordlist = response.items[0]
              selectedWordlist.value = firstWordlist.id
              console.log('🧭 Selected first wordlist:', firstWordlist.name)
              navigateToWordlist(firstWordlist.id, undefined, wordlistConfig.query)
            } else {
              console.log('🧭 No wordlists available, staying on home')
              navigateToHome()
            }
          } catch (error) {
            console.error('🧭 Failed to fetch wordlists:', error)
            navigateToHome()
          }
        }
        break
      }
      
      case 'word-of-the-day': {
        const wotdConfig = config as WordOfTheDayModeConfig
        console.log('🧭 Navigating to word-of-the-day with query:', wotdConfig.query)
        navigateToWordOfTheDay(wotdConfig.query)
        break
      }
      
      case 'stage': {
        const stageConfig = config as StageModeConfig
        console.log('🧭 Navigating to stage with query:', stageConfig.query)
        navigateToStage(stageConfig.query)
        break
      }
      
      default:
        console.log('🧭 Unknown mode, going to home')
        navigateToHome()
    }
  }

  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  // Enhanced search mode management with type-safe configuration
  const setSearchMode = async <T extends SearchMode>(
    options: ModeOperationOptions<T>
  ): Promise<ModeTransitionResult> => {
    const { mode: newMode, config, saveCurrentQuery = true, force = false } = options
    const previousMode = searchMode.value
    
    console.log('🔄 setSearchMode called:', previousMode, '->', newMode)
    
    if (searchMode.value === newMode && !force) {
      console.log('⚠️ Mode is already', newMode, '- no change needed')
      return {
        success: true,
        previousMode,
        newMode,
        navigationSuccess: true
      }
    }

    console.log('🔄 Actually changing searchMode from', searchMode.value, 'to', newMode)
    searchMode.value = newMode
    
    // Force reactivity trigger
    await nextTick()
    
    // Handle type-safe router navigation
    let navigationSuccess = true
    
    if (config?.router) {
      try {
        await handleModeNavigation(newMode, config)
      } catch (error) {
        console.error('🧭 setSearchMode: navigation failed:', error)
        navigationSuccess = false
      }
    }
    
    // Return structured result
    return {
      success: true,
      previousMode,
      newMode,
      navigationSuccess
    }
  }

  /**
   * Convenience function for legacy compatibility
   * @deprecated Use setSearchMode with ModeOperationOptions instead
   */
  const setSearchModeLegacy = async (
    newMode: SearchMode,
    router?: any,
    currentEntry?: any,
    mode?: string,
    modeQuery?: string,
    currentFilters?: Record<string, any>
  ): Promise<ModeTransitionResult> => {
    console.warn('⚠️ setSearchModeLegacy is deprecated. Please use setSearchMode with ModeOperationOptions.')
    
    // Convert legacy parameters to new format
    const config: any = {
      router,
      currentEntry,
      query: modeQuery
    }
    
    // Add mode-specific configurations
    if (newMode === 'lookup' && mode) {
      config.displayMode = mode
    } else if (newMode === 'wordlist' && currentFilters) {
      config.filters = currentFilters.filters
      config.chunking = currentFilters.chunking
      config.sortCriteria = currentFilters.sortCriteria
    }
    
    return setSearchMode({ mode: newMode, config })
  }

  const toggleSearchMode = async (router?: any, currentEntry?: any, mode?: string) => {
    console.log('🔄 toggleSearchMode called:', searchMode.value)
    
    // Cycle through modes: lookup -> wordlist -> word-of-the-day -> stage -> lookup
    let newMode: SearchMode
    if (searchMode.value === 'lookup') {
      newMode = 'wordlist'
    } else if (searchMode.value === 'wordlist') {
      newMode = 'word-of-the-day'
    } else if (searchMode.value === 'word-of-the-day') {
      newMode = 'stage'
    } else {
      newMode = 'lookup'
    }
    
    await setSearchMode(newMode, router, currentEntry, mode)
  }

  // Source management
  const toggleSource = (source: string) => {
    const sources = selectedSources.value
    if (sources.includes(source)) {
      selectedSources.value = sources.filter((s: string) => s !== source)
    } else {
      selectedSources.value = [...sources, source]
    }
  }

  const setSources = (sources: string[]) => {
    selectedSources.value = [...sources]
  }

  // Language management
  const toggleLanguage = (language: string) => {
    const languages = selectedLanguages.value
    if (languages.includes(language)) {
      selectedLanguages.value = languages.filter((l: string) => l !== language)
    } else {
      selectedLanguages.value = [...languages, language]
    }
  }

  const setLanguages = (languages: string[]) => {
    selectedLanguages.value = [...languages]
  }

  // Wordlist management
  const setWordlist = (wordlistId: string | null) => {
    selectedWordlist.value = wordlistId
  }

  // AI configuration
  const toggleAI = () => {
    noAI.value = !noAI.value
  }

  const setAI = (enabled: boolean) => {
    noAI.value = !enabled
  }

  // Control visibility
  const toggleControls = () => {
    showControls.value = !showControls.value
  }

  const setShowControls = (show: boolean) => {
    showControls.value = show
  }

  // Reset configuration
  const resetConfig = () => {
    searchMode.value = 'lookup'
    selectedSources.value = ['wiktionary']
    selectedLanguages.value = ['en']
    selectedWordlist.value = null
    noAI.value = true
    showControls.value = false
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    searchMode: readonly(searchMode),
    selectedSources: readonly(selectedSources),
    selectedLanguages: readonly(selectedLanguages),
    selectedWordlist: readonly(selectedWordlist),
    noAI: readonly(noAI),
    showControls: readonly(showControls),
    
    // Actions - Enhanced with type safety
    setSearchMode,
    setSearchModeLegacy,  // Deprecated - for backward compatibility
    toggleSearchMode,
    toggleSource,
    setSources,
    toggleLanguage,
    setLanguages,
    setWordlist,
    toggleAI,
    setAI,
    toggleControls,
    setShowControls,
    resetConfig
  }
}, {
  persist: {
    key: 'search-config',
    pick: [
      'searchMode',
      'selectedSources', 
      'selectedLanguages',
      'selectedWordlist',
      'noAI',
      'showControls'
    ]
  }
})
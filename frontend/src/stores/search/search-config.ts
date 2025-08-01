import { defineStore } from 'pinia'
import { ref, readonly, nextTick } from 'vue'
import { useRouterSync } from '../composables/useRouterSync'
import { wordlistApi } from '@/api'

type SearchMode = 'lookup' | 'wordlist' | 'word-of-the-day' | 'stage'

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
  
  const { updateRouterForCurrentEntry, navigateToWordlist, navigateToHome } = useRouterSync()

  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  // Search mode management
  const setSearchMode = async (
    newMode: SearchMode,
    router?: any,
    currentEntry?: any,
    mode?: string
  ) => {
    console.log('🔄 setSearchMode called:', searchMode.value, '->', newMode)
    
    if (searchMode.value === newMode) {
      console.log('⚠️ Mode is already', newMode, '- no change needed')
      return
    }

    console.log('🔄 Actually changing searchMode from', searchMode.value, 'to', newMode)
    searchMode.value = newMode
    
    // Force reactivity trigger
    await nextTick()
    
    // Handle router navigation when setting search mode
    if (router) {
      if (newMode === 'lookup') {
        // Check if we're already on a definition/thesaurus route
        const currentRoute = router.currentRoute?.value
        const isOnDefinitionRoute = currentRoute?.name === 'Definition' || currentRoute?.name === 'Thesaurus'
        
        if (currentEntry?.word) {
          console.log('🧭 setSearchMode: updating router for existing lookup:', currentEntry.word)
          updateRouterForCurrentEntry(currentEntry, (mode as 'dictionary' | 'thesaurus' | 'suggestions') || 'dictionary', 'lookup')
        } else if (isOnDefinitionRoute) {
          console.log('🧭 setSearchMode: on definition route, letting it load')
        } else {
          console.log('🧭 setSearchMode: no current entry, going to home')
          navigateToHome()
        }
      } else if (newMode === 'wordlist') {
        if (selectedWordlist.value) {
          console.log('🧭 setSearchMode: navigating to existing wordlist:', selectedWordlist.value)
          navigateToWordlist(selectedWordlist.value)
        } else {
          // No wordlist selected, fetch available wordlists and select first one
          console.log('🧭 setSearchMode: no wordlist selected, fetching first available')
          try {
            const response = await wordlistApi.getWordlists({ limit: 1 })
            if (response.items && response.items.length > 0) {
              const firstWordlist = response.items[0]
              selectedWordlist.value = firstWordlist.id
              console.log('🧭 setSearchMode: selected first wordlist:', firstWordlist.name, firstWordlist.id)
              navigateToWordlist(firstWordlist.id)
            } else {
              console.log('🧭 setSearchMode: no wordlists available, staying on home')
              navigateToHome()
            }
          } catch (error) {
            console.error('🧭 setSearchMode: failed to fetch wordlists:', error)
            navigateToHome()
          }
        }
      } else {
        // For other modes, go to home for now
        navigateToHome()
      }
    }
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
    
    // Actions
    setSearchMode,
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
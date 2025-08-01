import { defineStore } from 'pinia'
import { ref, readonly } from 'vue'

interface SortCriterion {
  field: string
  direction: 'asc' | 'desc'
}

/**
 * UIStore - General UI state and preferences
 * Handles theme, sidebar, card variants, and other UI preferences
 * Uses modern Pinia persistence for automatic state saving
 */
export const useUIStore = defineStore('ui', () => {
  // ==========================================================================
  // PERSISTED UI STATE
  // ==========================================================================
  
  // Theme and appearance
  const theme = ref<'light' | 'dark'>('light')
  const selectedCardVariant = ref<'default' | 'gold' | 'silver' | 'bronze'>('default')
  
  // Display modes
  const mode = ref<'dictionary' | 'thesaurus' | 'suggestions'>('dictionary')
  const pronunciationMode = ref<'phonetic' | 'ipa'>('phonetic')
  
  // Sidebar state
  const sidebarOpen = ref(false)
  const sidebarCollapsed = ref(true)
  const sidebarActiveCluster = ref<string | null>('')
  const sidebarActivePartOfSpeech = ref<string | null>('')
  
  // Sidebar accordion states for different views
  const sidebarAccordionState = ref({
    lookup: [] as string[],
    wordlist: [] as string[],
    'word-of-the-day': [] as string[],
    stage: [] as string[],
  })
  
  // Wordlist display preferences
  const wordlistFilters = ref({
    showBronze: true,
    showSilver: true,
    showGold: true,
    showHotOnly: false,
    showDueOnly: false,
  })
  
  const wordlistChunking = ref({
    byMastery: false,
    byDate: false,
    byLastVisited: false,
    byFrequency: false,
  })
  
  const wordlistSortCriteria = ref<SortCriterion[]>([])

  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  // Theme management
  const toggleTheme = () => {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
  }

  const setTheme = (newTheme: 'light' | 'dark') => {
    theme.value = newTheme
  }

  // Card variant management
  const setCardVariant = (variant: 'default' | 'gold' | 'silver' | 'bronze') => {
    selectedCardVariant.value = variant
  }

  // Mode management
  const toggleMode = () => {
    // Cycle through dictionary -> thesaurus -> suggestions -> dictionary
    if (mode.value === 'dictionary') {
      mode.value = 'thesaurus'
    } else if (mode.value === 'thesaurus') {
      mode.value = 'suggestions'
    } else {
      mode.value = 'dictionary'
    }
  }

  const setMode = (newMode: 'dictionary' | 'thesaurus' | 'suggestions') => {
    mode.value = newMode
  }

  // Pronunciation mode management
  const togglePronunciation = () => {
    pronunciationMode.value = pronunciationMode.value === 'phonetic' ? 'ipa' : 'phonetic'
  }

  const setPronunciationMode = (newMode: 'phonetic' | 'ipa') => {
    pronunciationMode.value = newMode
  }

  // Sidebar management
  const toggleSidebar = () => {
    sidebarOpen.value = !sidebarOpen.value
  }

  const setSidebarOpen = (open: boolean) => {
    sidebarOpen.value = open
  }

  const setSidebarCollapsed = (collapsed: boolean) => {
    sidebarCollapsed.value = collapsed
  }

  const setSidebarActiveCluster = (cluster: string | null) => {
    sidebarActiveCluster.value = cluster
  }

  const setSidebarActivePartOfSpeech = (partOfSpeech: string | null) => {
    sidebarActivePartOfSpeech.value = partOfSpeech
  }

  // Accordion state management
  const setSidebarAccordionState = (
    view: 'lookup' | 'wordlist' | 'word-of-the-day' | 'stage',
    state: string[]
  ) => {
    sidebarAccordionState.value[view] = [...state]
  }

  const toggleAccordionItem = (
    view: 'lookup' | 'wordlist' | 'word-of-the-day' | 'stage',
    item: string
  ) => {
    const currentState = sidebarAccordionState.value[view]
    if (currentState.includes(item)) {
      sidebarAccordionState.value[view] = currentState.filter(i => i !== item)
    } else {
      sidebarAccordionState.value[view] = [...currentState, item]
    }
  }

  // Wordlist preferences
  const setWordlistFilters = (filters: Partial<typeof wordlistFilters.value>) => {
    wordlistFilters.value = { ...wordlistFilters.value, ...filters }
  }

  const toggleWordlistFilter = (filterName: keyof typeof wordlistFilters.value) => {
    wordlistFilters.value[filterName] = !wordlistFilters.value[filterName]
  }

  const setWordlistChunking = (chunking: Partial<typeof wordlistChunking.value>) => {
    wordlistChunking.value = { ...wordlistChunking.value, ...chunking }
  }

  const toggleWordlistChunking = (chunkingName: keyof typeof wordlistChunking.value) => {
    wordlistChunking.value[chunkingName] = !wordlistChunking.value[chunkingName]
  }

  const setWordlistSortCriteria = (criteria: SortCriterion[]) => {
    wordlistSortCriteria.value = [...criteria]
  }

  const addSortCriterion = (criterion: SortCriterion) => {
    wordlistSortCriteria.value.push(criterion)
  }

  const removeSortCriterion = (index: number) => {
    wordlistSortCriteria.value.splice(index, 1)
  }

  const clearSortCriteria = () => {
    wordlistSortCriteria.value = []
  }

  // Reset all UI state
  const resetUI = () => {
    theme.value = 'light'
    selectedCardVariant.value = 'default'
    mode.value = 'dictionary'
    pronunciationMode.value = 'phonetic'
    sidebarOpen.value = false
    sidebarCollapsed.value = true
    sidebarActiveCluster.value = ''
    sidebarActivePartOfSpeech.value = ''
    sidebarAccordionState.value = {
      lookup: [],
      wordlist: [],
      'word-of-the-day': [],
      stage: [],
    }
    wordlistFilters.value = {
      showBronze: true,
      showSilver: true,
      showGold: true,
      showHotOnly: false,
      showDueOnly: false,
    }
    wordlistChunking.value = {
      byMastery: false,
      byDate: false,
      byLastVisited: false,
      byFrequency: false,
    }
    wordlistSortCriteria.value = []
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    theme: readonly(theme),
    selectedCardVariant: readonly(selectedCardVariant),
    mode: readonly(mode),
    pronunciationMode: readonly(pronunciationMode),
    sidebarOpen: readonly(sidebarOpen),
    sidebarCollapsed: readonly(sidebarCollapsed),
    sidebarActiveCluster: readonly(sidebarActiveCluster),
    sidebarActivePartOfSpeech: readonly(sidebarActivePartOfSpeech),
    sidebarAccordionState: readonly(sidebarAccordionState),
    wordlistFilters: readonly(wordlistFilters),
    wordlistChunking: readonly(wordlistChunking),
    wordlistSortCriteria: readonly(wordlistSortCriteria),
    
    // Actions
    toggleTheme,
    setTheme,
    setCardVariant,
    toggleMode,
    setMode,
    togglePronunciation,
    setPronunciationMode,
    toggleSidebar,
    setSidebarOpen,
    setSidebarCollapsed,
    setSidebarActiveCluster,
    setSidebarActivePartOfSpeech,
    setSidebarAccordionState,
    toggleAccordionItem,
    setWordlistFilters,
    toggleWordlistFilter,
    setWordlistChunking,
    toggleWordlistChunking,
    setWordlistSortCriteria,
    addSortCriterion,
    removeSortCriterion,
    clearSortCriteria,
    resetUI
  }
}, {
  persist: {
    key: 'ui-state',
    pick: [
      'theme',
      'selectedCardVariant',
      'mode',
      'pronunciationMode',
      'sidebarOpen',
      'sidebarCollapsed',
      'sidebarActiveCluster',
      'sidebarActivePartOfSpeech',
      'sidebarAccordionState',
      'wordlistFilters',
      'wordlistChunking',
      'wordlistSortCriteria'
    ]
  }
})
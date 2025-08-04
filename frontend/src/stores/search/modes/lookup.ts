import { ref, readonly } from 'vue'
import type { ModeHandler } from '@/stores/types/mode-types'
import type { SearchMode } from '@/types'
import { 
  PronunciationModes, 
  DEFAULT_CARD_VARIANT, 
  DEFAULT_PRONUNCIATION_MODE,
  DEFAULT_SOURCES,
  DEFAULT_LANGUAGES,
  type CardVariant,
  type PronunciationMode,
  type DictionarySource,
  type Language
} from '@/stores/types/constants'

/**
 * Lookup mode unified store
 * Contains all lookup-specific configuration, search bar state, and UI preferences
 */
export function useLookupMode() {
  // ==========================================================================
  // CONFIGURATION STATE
  // ==========================================================================
  
  const selectedSources = ref<DictionarySource[]>(DEFAULT_SOURCES)
  const selectedLanguages = ref<Language[]>(DEFAULT_LANGUAGES)
  const noAI = ref(true)
  
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
    const variants = Object.values(CardVariants) as CardVariant[]
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
  // STATE MANAGEMENT
  // ==========================================================================
  
  const getConfig = () => ({
    selectedSources: selectedSources.value,
    selectedLanguages: selectedLanguages.value,
    noAI: noAI.value
  })
  
  const setConfig = (config: any) => {
    if (config.selectedSources) setSources(config.selectedSources)
    if (config.selectedLanguages) setLanguages(config.selectedLanguages)
    if (config.noAI !== undefined) noAI.value = config.noAI
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
    
    // Search Bar State
    isAIQuery: readonly(isAIQuery),
    showSparkle: readonly(showSparkle),
    aiSuggestions: readonly(aiSuggestions),
    
    // UI State
    selectedCardVariant: readonly(selectedCardVariant),
    pronunciationMode: readonly(pronunciationMode),
    
    // Configuration Actions
    toggleSource,
    setSources,
    toggleLanguage,
    setLanguages,
    toggleAI,
    setAI,
    
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
import { defineStore } from 'pinia'
import { ref, readonly, computed } from 'vue'

interface LoadingStageDefinition {
  progress: number
  label: string
  description: string
}

/**
 * LoadingStore - Loading states and progress tracking
 * Handles loading indicators, progress bars, stage definitions, and loading modals
 * Provides centralized loading state management with proper cleanup
 */
export const useLoadingStore = defineStore('loading', () => {
  // ==========================================================================
  // LOADING STATE (Non-persisted)
  // ==========================================================================
  
  // Primary loading states
  const isSearching = ref(false)
  const hasSearched = ref(false)
  const forceRefreshMode = ref(false)
  
  // Progress tracking
  const loadingProgress = ref(0)
  const loadingStage = ref('')
  const loadingCategory = ref('')
  const loadingStageDefinitions = ref<LoadingStageDefinition[]>([])
  
  // Modal visibility 
  const showLoadingModal = ref(false)
  
  // AI suggestions loading
  const isSuggestingWords = ref(false)
  const suggestionsProgress = ref(0)
  const suggestionsStage = ref('')
  const suggestionsCategory = ref('')
  const suggestionsStageDefinitions = ref<LoadingStageDefinition[]>([])
  
  // Session tracking
  const sessionStartTime = ref(Date.now())

  // ==========================================================================
  // COMPUTED PROPERTIES
  // ==========================================================================
  
  // Combined loading state for easy access
  const loadingState = computed(() => ({
    isSearching: isSearching.value,
    hasSearched: hasSearched.value,
    progress: loadingProgress.value,
    stage: loadingStage.value,
    category: loadingCategory.value,
    showModal: showLoadingModal.value,
    forceRefresh: forceRefreshMode.value,
    stageDefinitions: loadingStageDefinitions.value
  }))

  const suggestionsState = computed(() => ({
    isLoading: isSuggestingWords.value,
    progress: suggestionsProgress.value,
    stage: suggestionsStage.value,
    category: suggestionsCategory.value,
    stageDefinitions: suggestionsStageDefinitions.value
  }))

  // Check if any loading operation is active
  const isAnyLoading = computed(() => 
    isSearching.value || isSuggestingWords.value
  )

  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  // Primary loading management
  const startLoading = (stage = 'Loading...', showModal = false) => {
    isSearching.value = true
    loadingProgress.value = 0
    loadingStage.value = stage
    showLoadingModal.value = showModal
    hasSearched.value = true
  }

  const stopLoading = () => {
    isSearching.value = false
    showLoadingModal.value = false
    
    // Reset progress after a delay to show completion
    setTimeout(() => {
      loadingProgress.value = 0
      loadingStage.value = ''
      loadingCategory.value = ''
      loadingStageDefinitions.value = []
    }, 1000)
  }

  const updateProgress = (progress: number, stage?: string, message?: string) => {
    loadingProgress.value = Math.max(0, Math.min(100, progress))
    
    if (stage) {
      loadingStage.value = stage
    }
    
    if (message) {
      console.log(`Loading: ${stage || loadingStage.value} - ${progress}% - ${message}`)
    }
  }

  const setStageDefinitions = (category: string, stages: LoadingStageDefinition[]) => {
    loadingCategory.value = category
    loadingStageDefinitions.value = [...stages]
    console.log(`Received stage config for category: ${category}`, stages)
  }

  // AI suggestions loading management
  const startSuggestions = (stage = 'Generating suggestions...') => {
    isSuggestingWords.value = true
    suggestionsProgress.value = 0
    suggestionsStage.value = stage
  }

  const stopSuggestions = () => {
    isSuggestingWords.value = false
    
    // Reset progress after a delay to show completion
    setTimeout(() => {
      suggestionsProgress.value = 0
      suggestionsStage.value = ''
      suggestionsCategory.value = ''
      suggestionsStageDefinitions.value = []
    }, 1000)
  }

  const updateSuggestionsProgress = (progress: number, stage?: string, message?: string) => {
    suggestionsProgress.value = Math.max(0, Math.min(100, progress))
    
    if (stage) {
      suggestionsStage.value = stage
    }
    
    if (message) {
      console.log(`AI Suggestions: ${stage || suggestionsStage.value} - ${progress}% - ${message}`)
    }
  }

  const setSuggestionsStageDefinitions = (category: string, stages: LoadingStageDefinition[]) => {
    suggestionsCategory.value = category
    suggestionsStageDefinitions.value = [...stages]
    console.log(`Received suggestions stage config for category: ${category}`, stages)
  }

  // Modal management
  const showModal = () => {
    showLoadingModal.value = true
  }

  const hideModal = () => {
    showLoadingModal.value = false
  }

  // Force refresh management
  const enableForceRefresh = () => {
    forceRefreshMode.value = true
  }

  const disableForceRefresh = () => {
    forceRefreshMode.value = false
  }

  const toggleForceRefresh = () => {
    forceRefreshMode.value = !forceRefreshMode.value
  }

  // Search state management
  const setHasSearched = (searched: boolean) => {
    hasSearched.value = searched
  }

  // Session management
  const resetSession = () => {
    sessionStartTime.value = Date.now()
  }

  const getSessionDuration = () => {
    return Date.now() - sessionStartTime.value
  }

  // Combined reset
  const resetAllLoading = () => {
    isSearching.value = false
    hasSearched.value = false
    forceRefreshMode.value = false
    loadingProgress.value = 0
    loadingStage.value = ''
    loadingCategory.value = ''
    loadingStageDefinitions.value = []
    showLoadingModal.value = false
    
    isSuggestingWords.value = false
    suggestionsProgress.value = 0
    suggestionsStage.value = ''
    suggestionsCategory.value = ''
    suggestionsStageDefinitions.value = []
  }

  // Utility functions for testing
  const testProgressUpdate = () => {
    console.log('Testing progress updates...')
    startLoading('Test loading...', true)
    
    let progress = 0
    const interval = setInterval(() => {
      progress += 10
      updateProgress(progress, `Test progress: ${progress}%`)

      if (progress >= 100) {
        clearInterval(interval)
        setTimeout(() => {
          stopLoading()
        }, 1000)
      }
    }, 500)
  }

  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    isSearching: readonly(isSearching),
    hasSearched: readonly(hasSearched),
    forceRefreshMode: readonly(forceRefreshMode),
    loadingProgress: readonly(loadingProgress),
    loadingStage: readonly(loadingStage),
    loadingCategory: readonly(loadingCategory),
    loadingStageDefinitions: readonly(loadingStageDefinitions),
    showLoadingModal: readonly(showLoadingModal),
    isSuggestingWords: readonly(isSuggestingWords),
    suggestionsProgress: readonly(suggestionsProgress),
    suggestionsStage: readonly(suggestionsStage),
    suggestionsCategory: readonly(suggestionsCategory),
    suggestionsStageDefinitions: readonly(suggestionsStageDefinitions),
    sessionStartTime: readonly(sessionStartTime),
    
    // Computed
    loadingState,
    suggestionsState,
    isAnyLoading,
    
    // Actions
    startLoading,
    stopLoading,
    updateProgress,
    setStageDefinitions,
    startSuggestions,
    stopSuggestions,
    updateSuggestionsProgress,
    setSuggestionsStageDefinitions,
    showModal,
    hideModal,
    enableForceRefresh,
    disableForceRefresh,
    toggleForceRefresh,
    setHasSearched,
    resetSession,
    getSessionDuration,
    resetAllLoading,
    testProgressUpdate
  }
})
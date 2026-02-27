import { ref, readonly, computed } from 'vue'

// Global loading state (module-level singletons)
const _isLoading = ref(false)
const _isSearching = ref(false)
const _loadingProgress = ref(0)
const _loadingStage = ref('')
const _loadingStageDefinitions = ref<Record<string, number>>({})
const _loadingCategory = ref('')
const _showLoadingModal = ref(false)
const _isSuggestingWords = ref(false)
const _suggestionsProgress = ref(0)
const _suggestionsStage = ref('')
const _suggestionsStageDefinitions = ref<Record<string, number>>({})
const _suggestionsCategory = ref('')
const _forceRefreshMode = ref(false)

// Concurrency guard
const _activeOperations = ref(0)

export function useLoadingState() {
  // --- Setters ---
  const setLoading = (loading: boolean) => {
    _isLoading.value = loading
  }

  const setSearching = (searching: boolean) => {
    _isSearching.value = searching
  }

  const setLoadingProgress = (progress: number) => {
    _loadingProgress.value = progress
  }

  const setLoadingStage = (stage: string) => {
    _loadingStage.value = stage
  }

  const setLoadingStageDefinitions = (definitions: Record<string, number>) => {
    _loadingStageDefinitions.value = definitions
  }

  const setLoadingCategory = (category: string) => {
    _loadingCategory.value = category
  }

  const setShowLoadingModal = (show: boolean) => {
    _showLoadingModal.value = show
  }

  const setSuggestingWords = (suggesting: boolean) => {
    _isSuggestingWords.value = suggesting
  }

  const setSuggestionsProgress = (progress: number) => {
    _suggestionsProgress.value = progress
  }

  const setSuggestionsStage = (stage: string) => {
    _suggestionsStage.value = stage
  }

  const setSuggestionsStageDefinitions = (definitions: Record<string, number>) => {
    _suggestionsStageDefinitions.value = definitions
  }

  const setSuggestionsCategory = (category: string) => {
    _suggestionsCategory.value = category
  }

  const setForceRefreshMode = (force: boolean) => {
    _forceRefreshMode.value = force
  }

  // --- Operation lifecycle ---
  const startOperation = () => {
    _activeOperations.value++
    _isSearching.value = true
    _isLoading.value = true
  }

  const endOperation = () => {
    _activeOperations.value = Math.max(0, _activeOperations.value - 1)
    if (_activeOperations.value === 0) {
      _isSearching.value = false
      _isLoading.value = false
    }
  }

  const isOperationActive = computed(() => _activeOperations.value > 0)

  // --- Batch operations ---
  const stopSuggestions = () => {
    _isSuggestingWords.value = false
    _suggestionsProgress.value = 0
    _suggestionsStage.value = ''
    _suggestionsCategory.value = ''
  }

  const resetLoading = () => {
    _isLoading.value = false
    _isSearching.value = false
    _loadingProgress.value = 0
    _loadingStage.value = ''
    _loadingCategory.value = ''
    _showLoadingModal.value = false
    _activeOperations.value = 0
  }

  return {
    // All state as readonly
    isLoading: readonly(_isLoading),
    isSearching: readonly(_isSearching),
    loadingProgress: readonly(_loadingProgress),
    loadingStage: readonly(_loadingStage),
    loadingStageDefinitions: readonly(_loadingStageDefinitions),
    loadingCategory: readonly(_loadingCategory),
    showLoadingModal: readonly(_showLoadingModal),
    isSuggestingWords: readonly(_isSuggestingWords),
    suggestionsProgress: readonly(_suggestionsProgress),
    suggestionsStage: readonly(_suggestionsStage),
    suggestionsStageDefinitions: readonly(_suggestionsStageDefinitions),
    suggestionsCategory: readonly(_suggestionsCategory),
    forceRefreshMode: readonly(_forceRefreshMode),
    isOperationActive,

    // Setters
    setLoading,
    setSearching,
    setLoadingProgress,
    setLoadingStage,
    setLoadingStageDefinitions,
    setLoadingCategory,
    setShowLoadingModal,
    setSuggestingWords,
    setSuggestionsProgress,
    setSuggestionsStage,
    setSuggestionsStageDefinitions,
    setSuggestionsCategory,
    setForceRefreshMode,

    // Operation lifecycle
    startOperation,
    endOperation,

    // Batch operations
    stopSuggestions,
    resetLoading,
  }
}

// Alias for backward compatibility
export const useLoadingStore = useLoadingState

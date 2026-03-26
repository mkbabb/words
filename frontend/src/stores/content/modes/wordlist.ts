import { ref, readonly, shallowRef } from 'vue'
import type { WordlistContentState, ModeHandler } from '@/stores/types/mode-types'
import type { SearchMode, WordList, SynthesizedDictionaryEntry } from '@/types'

/**
 * Wordlist mode content state
 * Handles wordlist data, processing queues, and batch results
 */
export function useWordlistContentState() {
  // ==========================================================================
  // WORDLIST-SPECIFIC CONTENT STATE
  // ==========================================================================
  
  const currentWordlist = shallowRef<WordList | null>(null)
  const processingQueue = ref<string[]>([])
  const batchResults = shallowRef<Map<string, SynthesizedDictionaryEntry>>(new Map())

  // Review session state
  const reviewSessionState = ref<{
    sessionId: string | null
    words: any[]
    currentIndex: number
    results: any[]
    startedAt: string | null
    estimatedTimeMinutes: number
    difficultyDistribution: Record<string, number>
  }>({
    sessionId: null,
    words: [],
    currentIndex: 0,
    results: [],
    startedAt: null,
    estimatedTimeMinutes: 0,
    difficultyDistribution: {},
  })

  // Batch progress tracking
  const batchProgress = ref<{
    totalWords: number
    processedWords: number
    startTime: number | null
    estimatedEta: number | null
    retryCount: number
  }>({
    totalWords: 0,
    processedWords: 0,
    startTime: null,
    estimatedEta: null,
    retryCount: 0,
  })
  
  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  const setCurrentWordlist = (wordlist: WordList | null) => {
    currentWordlist.value = wordlist
  }
  
  const addToProcessingQueue = (word: string) => {
    if (!processingQueue.value.includes(word)) {
      processingQueue.value = [...processingQueue.value, word]
    }
  }
  
  const removeFromProcessingQueue = (word: string) => {
    processingQueue.value = processingQueue.value.filter(w => w !== word)
  }
  
  const clearProcessingQueue = () => {
    processingQueue.value = []
  }
  
  const setBatchResult = (word: string, result: SynthesizedDictionaryEntry) => {
    const newMap = new Map(batchResults.value)
    newMap.set(word, result)
    batchResults.value = newMap
  }
  
  const getBatchResult = (word: string) => {
    return batchResults.value.get(word)
  }
  
  const clearBatchResults = () => {
    batchResults.value = new Map()
  }

  // Review session actions
  const setReviewSession = (session: Partial<typeof reviewSessionState.value>) => {
    reviewSessionState.value = { ...reviewSessionState.value, ...session }
  }

  const advanceReviewIndex = () => {
    if (reviewSessionState.value.currentIndex < reviewSessionState.value.words.length - 1) {
      reviewSessionState.value.currentIndex++
    }
  }

  const addReviewResult = (result: any) => {
    reviewSessionState.value.results = [...reviewSessionState.value.results, result]
  }

  const resetReviewSession = () => {
    reviewSessionState.value = {
      sessionId: null,
      words: [],
      currentIndex: 0,
      results: [],
      startedAt: null,
      estimatedTimeMinutes: 0,
      difficultyDistribution: {},
    }
  }

  // Batch progress actions
  const setBatchProgress = (progress: Partial<typeof batchProgress.value>) => {
    batchProgress.value = { ...batchProgress.value, ...progress }
  }

  const incrementBatchProgress = () => {
    batchProgress.value.processedWords++
    if (batchProgress.value.startTime && batchProgress.value.totalWords > 0) {
      const elapsed = Date.now() - batchProgress.value.startTime
      const rate = batchProgress.value.processedWords / elapsed
      const remaining = batchProgress.value.totalWords - batchProgress.value.processedWords
      batchProgress.value.estimatedEta = remaining / rate
    }
  }

  const resetBatchProgress = () => {
    batchProgress.value = {
      totalWords: 0,
      processedWords: 0,
      startTime: null,
      estimatedEta: null,
      retryCount: 0,
    }
  }
  
  const getState = (): WordlistContentState => ({
    currentWordlist: currentWordlist.value,
    processingQueue: [...processingQueue.value],
    batchResults: new Map(batchResults.value)
  })
  
  const setState = (state: Partial<WordlistContentState>) => {
    if (state.currentWordlist !== undefined) setCurrentWordlist(state.currentWordlist)
    if (state.processingQueue) processingQueue.value = [...state.processingQueue]
    if (state.batchResults) batchResults.value = new Map(state.batchResults)
  }
  
  const reset = () => {
    currentWordlist.value = null
    processingQueue.value = []
    batchResults.value = new Map()
    resetReviewSession()
    resetBatchProgress()
  }
  
  // ==========================================================================
  // MODE HANDLER
  // ==========================================================================
  
  const handler: ModeHandler<WordlistContentState> = {
    onEnter: async (_previousMode: SearchMode) => {
    },

    onExit: async (_nextMode: SearchMode) => {
      // Clear batch results and review session when leaving
      clearBatchResults()
      resetReviewSession()
      resetBatchProgress()
    },

    getDefaultState: () => ({
      currentWordlist: null,
      processingQueue: [],
      batchResults: new Map()
    })
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    currentWordlist: readonly(currentWordlist),
    processingQueue: readonly(processingQueue),
    batchResults: readonly(batchResults),
    reviewSessionState: readonly(reviewSessionState),
    batchProgress: readonly(batchProgress),

    // Actions
    setCurrentWordlist,
    addToProcessingQueue,
    removeFromProcessingQueue,
    clearProcessingQueue,
    setBatchResult,
    getBatchResult,
    clearBatchResults,

    // Review session actions
    setReviewSession,
    advanceReviewIndex,
    addReviewResult,
    resetReviewSession,

    // Batch progress actions
    setBatchProgress,
    incrementBatchProgress,
    resetBatchProgress,

    // State management
    getState,
    setState,
    reset,

    // Mode handler
    handler
  }
}
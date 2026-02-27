import { ref, readonly, shallowRef } from 'vue'
import type { WordlistContentState, ModeHandler } from '@/stores/types/mode-types'
import type { SearchMode } from '@/types'

/**
 * Wordlist mode content state
 * Handles wordlist data, processing queues, and batch results
 */
export function useWordlistContentState() {
  // ==========================================================================
  // WORDLIST-SPECIFIC CONTENT STATE
  // ==========================================================================
  
  const currentWordlist = shallowRef<any | null>(null)
  const processingQueue = ref<string[]>([])
  const batchResults = shallowRef<Map<string, any>>(new Map())
  
  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  const setCurrentWordlist = (wordlist: any | null) => {
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
  
  const setBatchResult = (word: string, result: any) => {
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
  }
  
  // ==========================================================================
  // MODE HANDLER
  // ==========================================================================
  
  const handler: ModeHandler<WordlistContentState> = {
    onEnter: async (_previousMode: SearchMode) => {
    },

    onExit: async (_nextMode: SearchMode) => {
      // Clear batch results when leaving
      clearBatchResults()
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
    
    // Actions
    setCurrentWordlist,
    addToProcessingQueue,
    removeFromProcessingQueue,
    clearProcessingQueue,
    setBatchResult,
    getBatchResult,
    clearBatchResults,
    
    // State management
    getState,
    setState,
    reset,
    
    // Mode handler
    handler
  }
}
import { ref, readonly, shallowRef } from 'vue'
import type { LookupContentState, ModeHandler } from '@/stores/types/mode-types'
import type { SearchMode, SynthesizedDictionaryEntry, ThesaurusEntry, WordSuggestionResponse } from '@/types'

/**
 * Lookup mode content state
 * Handles dictionary entries, thesaurus data, word suggestions, and streaming
 */
export function useLookupContentState() {
  // ==========================================================================
  // LOOKUP-SPECIFIC CONTENT STATE
  // ==========================================================================
  
  const currentEntry = shallowRef<SynthesizedDictionaryEntry | null>(null)
  const currentThesaurus = shallowRef<ThesaurusEntry | null>(null)
  const wordSuggestions = shallowRef<WordSuggestionResponse | null>(null)
  const partialEntry = shallowRef<Partial<SynthesizedDictionaryEntry> | null>(null)
  const isStreamingData = ref(false)
  
  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  const setCurrentEntry = (entry: SynthesizedDictionaryEntry | null) => {
    currentEntry.value = entry
  }
  
  const setCurrentThesaurus = (thesaurus: ThesaurusEntry | null) => {
    currentThesaurus.value = thesaurus
  }
  
  const setWordSuggestions = (suggestions: WordSuggestionResponse | null) => {
    wordSuggestions.value = suggestions
  }
  
  const setPartialEntry = (entry: Partial<SynthesizedDictionaryEntry> | null) => {
    partialEntry.value = entry
  }
  
  const setStreamingState = (streaming: boolean) => {
    isStreamingData.value = streaming
  }
  
  const clearCurrentEntry = () => {
    currentEntry.value = null
    currentThesaurus.value = null
    partialEntry.value = null
  }
  
  const clearWordSuggestions = () => {
    wordSuggestions.value = null
  }
  
  const getState = (): LookupContentState => ({
    currentEntry: currentEntry.value,
    currentThesaurus: currentThesaurus.value,
    wordSuggestions: wordSuggestions.value,
    partialEntry: partialEntry.value,
    isStreamingData: isStreamingData.value
  })
  
  const setState = (state: Partial<LookupContentState>) => {
    if (state.currentEntry !== undefined) setCurrentEntry(state.currentEntry)
    if (state.currentThesaurus !== undefined) setCurrentThesaurus(state.currentThesaurus)
    if (state.wordSuggestions !== undefined) setWordSuggestions(state.wordSuggestions)
    if (state.partialEntry !== undefined) setPartialEntry(state.partialEntry)
    if (state.isStreamingData !== undefined) setStreamingState(state.isStreamingData)
  }
  
  const reset = () => {
    currentEntry.value = null
    currentThesaurus.value = null
    wordSuggestions.value = null
    partialEntry.value = null
    isStreamingData.value = false
  }
  
  // ==========================================================================
  // MODE HANDLER
  // ==========================================================================
  
  const handler: ModeHandler<LookupContentState> = {
    onEnter: async (previousMode: SearchMode) => {
      console.log('📖 Content entering lookup mode from:', previousMode)
    },
    
    onExit: async (nextMode: SearchMode) => {
      console.log('👋 Content exiting lookup mode to:', nextMode)
      // Stop any streaming when leaving
      isStreamingData.value = false
    },
    
    getDefaultState: () => ({
      currentEntry: null,
      currentThesaurus: null,
      wordSuggestions: null,
      partialEntry: null,
      isStreamingData: false
    })
  }
  
  // ==========================================================================
  // RETURN API
  // ==========================================================================
  
  return {
    // State
    currentEntry: readonly(currentEntry),
    currentThesaurus: readonly(currentThesaurus),
    wordSuggestions: readonly(wordSuggestions),
    partialEntry: readonly(partialEntry),
    isStreamingData: readonly(isStreamingData),
    
    // Actions
    setCurrentEntry,
    setCurrentThesaurus,
    setWordSuggestions,
    setPartialEntry,
    setStreamingState,
    clearCurrentEntry,
    clearWordSuggestions,
    
    // State management
    getState,
    setState,
    reset,
    
    // Mode handler
    handler
  }
}
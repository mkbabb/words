import { ref, readonly, shallowRef } from 'vue'
import { dictionaryApi } from '@/api'
import type { LookupContentState, ModeHandler } from '@/stores/types/mode-types'
import type { SearchMode, SynthesizedDictionaryEntry, ThesaurusEntry, WordSuggestionResponse, Definition } from '@/types'

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
  
  // Operation state
  const regeneratingDefinitionIndex = ref<number | null>(null)
  
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
    regeneratingDefinitionIndex.value = null
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
    regeneratingDefinitionIndex.value = null
  }
  
  // ==========================================================================
  // CONTENT OPERATIONS
  // ==========================================================================
  
  const updateDefinition = async (definitionId: string, updates: Partial<Definition>) => {
    const response = await dictionaryApi.updateDefinition(definitionId, updates)
    
    if (currentEntry.value?.definitions?.some(def => def.id === definitionId)) {
      const updatedEntry = {
        ...currentEntry.value,
        definitions: currentEntry.value.definitions.map(def => 
          def.id === definitionId ? { ...def, ...response } : def
        )
      }
      setCurrentEntry(updatedEntry)
    }
    
    return response
  }

  const updateExample = async (_definitionId: string, exampleId: string, newText: string) => {
    const response = await dictionaryApi.updateExample(exampleId, { text: newText })
    
    if (currentEntry.value) {
      // For now, just trigger a refresh since nested updates are complex
      const updatedEntry = { ...currentEntry.value }
      setCurrentEntry(updatedEntry)
    }
    
    return response
  }

  const regenerateDefinitionComponent = async (definitionId: string, component: 'definition' | 'examples' | 'usage_notes') => {
    const response = await dictionaryApi.regenerateDefinitionComponent(definitionId, component)
    
    if (currentEntry.value) {
      const updatedEntry = {
        ...currentEntry.value,
        definitions: currentEntry.value.definitions?.map(def => 
          def.id === definitionId 
            ? { ...def, [component]: response[component] } 
            : def
        )
      }
      setCurrentEntry(updatedEntry)
    }
    
    return response
  }

  const regenerateExamples = async (definitionIndex: number) => {
    if (!currentEntry.value?.definitions?.[definitionIndex]) return
    
    // Prevent concurrent operations
    if (regeneratingDefinitionIndex.value !== null) return
    
    const definition = currentEntry.value.definitions[definitionIndex]
    regeneratingDefinitionIndex.value = definitionIndex
    
    try {
      const response = await dictionaryApi.regenerateExamples(
        currentEntry.value.word,
        definitionIndex
      )
      
      const updatedEntry = { ...currentEntry.value }
      if (updatedEntry.definitions) {
        updatedEntry.definitions[definitionIndex] = {
          ...definition,
          examples: response.examples as any
        }
        setCurrentEntry(updatedEntry)
      }
      
      return response
    } finally {
      regeneratingDefinitionIndex.value = null
    }
  }

  const refreshEntryImages = async () => {
    if (!currentEntry.value) return
    
    const response = await dictionaryApi.refreshSynthEntry(currentEntry.value.word)
    
    const updatedEntry: SynthesizedDictionaryEntry = {
      ...currentEntry.value,
      ...response
    } as any // Type assertion needed due to complex merge
    
    setCurrentEntry(updatedEntry)
    return response
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
    regeneratingDefinitionIndex: readonly(regeneratingDefinitionIndex),
    
    // Actions
    setCurrentEntry,
    setCurrentThesaurus,
    setWordSuggestions,
    setPartialEntry,
    setStreamingState,
    clearCurrentEntry,
    clearWordSuggestions,
    
    // Content operations
    updateDefinition,
    updateExample,
    regenerateDefinitionComponent,
    regenerateExamples,
    refreshEntryImages,
    
    // State management
    getState,
    setState,
    reset,
    
    // Mode handler
    handler
  }
}
import { ref, readonly, shallowRef } from 'vue'
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
  
  // Progressive sidebar state (for scroll-based highlighting)
  const sidebarActiveCluster = ref<string | null>('')
  const sidebarActivePartOfSpeech = ref<string | null>('')
  
  // ==========================================================================
  // ACTIONS
  // ==========================================================================
  
  const setSidebarActiveCluster = (cluster: string | null) => {
    sidebarActiveCluster.value = cluster
  }
  
  const setSidebarActivePartOfSpeech = (partOfSpeech: string | null) => {
    sidebarActivePartOfSpeech.value = partOfSpeech
  }
  
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
  // PURE STATE MUTATIONS (no API calls — network logic lives in composables)
  // ==========================================================================

  const setRegeneratingDefinitionIndex = (index: number | null) => {
    regeneratingDefinitionIndex.value = index
  }

  /**
   * Apply a definition update to the local entry state.
   * Called by useContentMutations after a successful API call.
   */
  const applyDefinitionUpdate = (definitionId: string, updates: Partial<Definition>) => {
    if (currentEntry.value?.definitions?.some(def => def.id === definitionId)) {
      const updatedEntry = {
        ...currentEntry.value,
        definitions: currentEntry.value.definitions.map(def =>
          def.id === definitionId ? { ...def, ...updates } : def
        )
      } as SynthesizedDictionaryEntry
      setCurrentEntry(updatedEntry)
    }
  }

  /**
   * Trigger a shallow refresh of currentEntry so the UI picks up nested changes.
   */
  const touchCurrentEntry = () => {
    if (currentEntry.value) {
      setCurrentEntry({ ...currentEntry.value })
    }
  }

  /**
   * Apply a regenerated component to the matching definition.
   */
  const applyDefinitionComponentRegeneration = (
    definitionId: string,
    component: string,
    response: Record<string, unknown>
  ) => {
    if (currentEntry.value) {
      const updatedEntry = {
        ...currentEntry.value,
        definitions: currentEntry.value.definitions?.map(def =>
          def.id === definitionId
            ? { ...def, [component]: response[component] }
            : def
        )
      } as SynthesizedDictionaryEntry
      setCurrentEntry(updatedEntry)
    }
  }

  /**
   * Apply regenerated examples at a specific definition index.
   */
  const applyExamplesRegeneration = (definitionIndex: number, response: { examples?: unknown }) => {
    if (!currentEntry.value?.definitions?.[definitionIndex]) return

    const definition = currentEntry.value.definitions[definitionIndex]
    const updatedEntry = { ...currentEntry.value }
    if (updatedEntry.definitions) {
      updatedEntry.definitions[definitionIndex] = {
        ...definition,
        examples: response.examples as any
      }
      setCurrentEntry(updatedEntry)
    }
  }
  
  // ==========================================================================
  // MODE HANDLER
  // ==========================================================================
  
  const handler: ModeHandler<LookupContentState> = {
    onEnter: async (_previousMode: SearchMode) => {
    },

    onExit: async (_nextMode: SearchMode) => {
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
    
    // Progressive sidebar state
    sidebarActiveCluster: readonly(sidebarActiveCluster),
    sidebarActivePartOfSpeech: readonly(sidebarActivePartOfSpeech),
    
    // Actions
    setCurrentEntry,
    setCurrentThesaurus,
    setWordSuggestions,
    setPartialEntry,
    setStreamingState,
    clearCurrentEntry,
    clearWordSuggestions,
    
    // Pure state mutations (API calls live in useContentMutations composable)
    setRegeneratingDefinitionIndex,
    applyDefinitionUpdate,
    touchCurrentEntry,
    applyDefinitionComponentRegeneration,
    applyExamplesRegeneration,
    
    // Sidebar actions
    setSidebarActiveCluster,
    setSidebarActivePartOfSpeech,
    
    // State management
    getState,
    setState,
    reset,
    
    // Mode handler
    handler
  }
}